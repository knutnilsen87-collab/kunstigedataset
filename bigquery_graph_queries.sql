-- =============================================================================
-- BigQuery Graph Analytics & GQL Reference for AML Property Dataset
-- Dataset: datsetsyntetisk.aml_synth
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. DDL: Definere Property Graph
-- -----------------------------------------------------------------------------
CREATE OR REPLACE PROPERTY GRAPH `datsetsyntetisk.aml_synth.aml_network_graph`
  NODE TABLES (
    `datsetsyntetisk.aml_synth.entities` AS Entity
      KEY (id)
      LABEL Entity
      PROPERTIES (id, type)
  )
  EDGE TABLES (
    `datsetsyntetisk.aml_synth.ownership_edges` AS OwnershipEdge
      KEY (source, target, role)
      SOURCE KEY (source) REFERENCES Entity (id)
      DESTINATION KEY (target) REFERENCES Entity (id)
      LABEL OwnershipEdge
      PROPERTIES (role),
    `datsetsyntetisk.aml_synth.transactions` AS Transfer
      KEY (id)
      SOURCE KEY (sender) REFERENCES Entity (id)
      DESTINATION KEY (receiver) REFERENCES Entity (id)
      LABEL Transfer
      PROPERTIES (id, amount, type)
  );

-- -----------------------------------------------------------------------------
-- 2. GQL Spørringer (Krever BigQuery Enterprise / Enterprise Plus Edition)
-- -----------------------------------------------------------------------------

-- GQL 1: Traverser 1-3 lag holdingselskaper fra reell eier (UBO) til eiendom
/*
GRAPH `datsetsyntetisk.aml_synth.aml_network_graph`
MATCH (ubo:Entity)-[s:OwnershipEdge {role: 'shareholder'}]->{1,3}(prop_co:Entity)-[reg:OwnershipEdge {role: 'registered_owner'}]->(prop:Entity)
RETURN 
  ubo.id AS ubo_id,
  prop_co.id AS prop_co_id,
  prop.id AS property_id,
  ARRAY_LENGTH(s) AS chain_depth;
*/

-- GQL 2: Detekter sirkulære låneavtaler (Loan-back scheme)
/*
GRAPH `datsetsyntetisk.aml_synth.aml_network_graph`
MATCH (mastermind:Entity)-[:OwnershipEdge {role: 'actual_controller'}]->(lender:Entity),
      (lender)-[:OwnershipEdge {role: 'mortgage_holder'}]->(prop:Entity),
      (borrower:Entity)-[:OwnershipEdge {role: 'registered_owner'}]->(prop),
      (lender)-[disb:Transfer {type: 'loan_disbursement'}]->(borrower),
      (borrower)-[repay:Transfer {type: 'loan_installment'}]->(lender)
RETURN 
  mastermind.id AS hidden_lender_id,
  lender.id AS shell_lender_id,
  borrower.id AS borrower_id,
  prop.id AS property_id,
  disb.amount AS loan_amount,
  repay.amount AS repayment_amount;
*/

-- GQL 3: Blankoskjøte med direkte bakmannsfinansiering
/*
GRAPH `datsetsyntetisk.aml_synth.aml_network_graph`
MATCH (strawman:Entity)-[:OwnershipEdge {role: 'registered_owner'}]->(prop:Entity),
      (hidden:Entity)-[:OwnershipEdge {role: 'actual_controller'}]->(prop),
      (hidden)-[fin:Transfer {type: 'transfer'}]->(strawman)
WHERE strawman.id != hidden.id
RETURN 
  prop.id AS property_id,
  strawman.id AS strawman_id,
  hidden.id AS hidden_controller_id,
  fin.amount AS financing_nok;
*/

-- -----------------------------------------------------------------------------
-- 3. Standard GoogleSQL Ekvivalenter (Kjører på ALLE BigQuery-utgaver, inkl. On-Demand)
-- -----------------------------------------------------------------------------

-- SQL 1: Rekursiv traversering av lagdelte selskaper (Holding Chains)
WITH RECURSIVE holding_hierarchy AS (
  SELECT
    oe.source AS shareholder,
    oe.target AS company,
    prop_edge.target AS property_id,
    1 AS depth,
    CONCAT(oe.source, ' -> ', oe.target) AS path
  FROM `datsetsyntetisk.aml_synth.ownership_edges` oe
  JOIN `datsetsyntetisk.aml_synth.ownership_edges` prop_edge
    ON oe.target = prop_edge.source
    AND prop_edge.role = 'registered_owner'
  WHERE oe.role = 'shareholder'

  UNION ALL

  SELECT
    parent_oe.source AS shareholder,
    hh.company,
    hh.property_id,
    hh.depth + 1 AS depth,
    CONCAT(parent_oe.source, ' -> ', hh.path) AS path
  FROM `datsetsyntetisk.aml_synth.ownership_edges` parent_oe
  JOIN holding_hierarchy hh
    ON parent_oe.target = hh.shareholder
  WHERE parent_oe.role = 'shareholder'
    AND hh.depth < 5
)
SELECT
  hh.property_id,
  hh.shareholder AS ultimate_beneficial_owner,
  ctrl.source AS actual_controller,
  hh.depth AS holding_layers,
  hh.path AS corporate_chain
FROM holding_hierarchy hh
JOIN `datsetsyntetisk.aml_synth.ownership_edges` ctrl
  ON hh.property_id = ctrl.target
  AND hh.shareholder = ctrl.source
  AND ctrl.role = 'actual_controller'
WHERE hh.depth >= 2;

-- SQL 2: Loan-Back Mortgage Deteksjon
SELECT
  m.target AS property_id,
  m.source AS lender_company,
  ctrl.source AS hidden_lender_mastermind,
  borrower.source AS borrower,
  disb.amount AS loan_amount,
  COUNT(repay.id) AS repayments_count,
  SUM(repay.amount) AS total_repaid_amount
FROM `datsetsyntetisk.aml_synth.ownership_edges` m
JOIN `datsetsyntetisk.aml_synth.ownership_edges` ctrl
  ON m.source = ctrl.target
  AND ctrl.role = 'actual_controller'
JOIN `datsetsyntetisk.aml_synth.ownership_edges` borrower
  ON m.target = borrower.target
  AND borrower.role = 'registered_owner'
JOIN `datsetsyntetisk.aml_synth.transactions` disb
  ON m.source = disb.sender
  AND borrower.source = disb.receiver
  AND disb.type = 'loan_disbursement'
LEFT JOIN `datsetsyntetisk.aml_synth.transactions` repay
  ON borrower.source = repay.sender
  AND m.source = repay.receiver
  AND repay.type = 'loan_installment'
WHERE m.role = 'mortgage_holder'
GROUP BY property_id, lender_company, hidden_lender_mastermind, borrower, loan_amount;
