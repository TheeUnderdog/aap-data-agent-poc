-- ============================================================================
-- AAP Loyalty POC — Semantic Views (Contract Layer)
-- ============================================================================
-- These views form the stable query interface for the Fabric Data Agent.
-- The Data Agent queries ONLY these views, never the raw mirrored tables.
-- Run this in the Fabric Lakehouse SQL endpoint after the sample data notebook.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS semantic;
GO

-- ----------------------------------------------------------------------------
-- 1. v_member_summary — Member profile with current tier, points, status
-- ----------------------------------------------------------------------------
CREATE OR ALTER VIEW semantic.v_member_summary AS
SELECT
    m.member_id,
    m.first_name,
    m.last_name,
    m.first_name + ' ' + m.last_name AS full_name,
    m.email,
    m.phone,
    m.enrollment_date,
    m.enrollment_source,
    m.member_status,
    m.tier,
    m.opt_in_email,
    m.opt_in_sms,
    m.diy_account_id,
    COALESCE(pb.current_balance, 0) AS current_points_balance,
    COALESCE(pb.lifetime_earned, 0) AS lifetime_points_earned,
    COALESCE(pb.lifetime_redeemed, 0) AS lifetime_points_redeemed,
    COALESCE(ts.transaction_count, 0) AS total_transactions,
    ts.total_spend,
    ts.first_purchase_date,
    ts.last_purchase_date,
    m.created_at,
    m.updated_at
FROM mirrored.loyalty_members m
LEFT JOIN (
    SELECT
        member_id,
        SUM(CASE WHEN points_amount > 0 THEN points_amount ELSE 0 END) AS lifetime_earned,
        SUM(CASE WHEN points_amount < 0 THEN ABS(points_amount) ELSE 0 END) AS lifetime_redeemed,
        SUM(points_amount) AS current_balance
    FROM mirrored.member_points
    GROUP BY member_id
) pb ON m.member_id = pb.member_id
LEFT JOIN (
    SELECT
        member_id,
        COUNT(*) AS transaction_count,
        SUM(CASE WHEN transaction_type = 'purchase' THEN total ELSE 0 END) AS total_spend,
        MIN(transaction_date) AS first_purchase_date,
        MAX(transaction_date) AS last_purchase_date
    FROM mirrored.transactions
    GROUP BY member_id
) ts ON m.member_id = ts.member_id;
GO

-- ----------------------------------------------------------------------------
-- 2. v_transaction_history — Transactions with member and store context
-- ----------------------------------------------------------------------------
CREATE OR ALTER VIEW semantic.v_transaction_history AS
SELECT
    t.transaction_id,
    t.member_id,
    m.first_name + ' ' + m.last_name AS member_name,
    m.tier AS member_tier,
    t.store_id,
    s.store_name,
    s.city AS store_city,
    s.state AS store_state,
    s.region AS store_region,
    t.transaction_date,
    t.transaction_type,
    t.subtotal,
    t.tax,
    t.total,
    t.item_count,
    t.channel,
    t.order_id,
    t.created_at
FROM mirrored.transactions t
JOIN mirrored.loyalty_members m ON t.member_id = m.member_id
JOIN mirrored.stores s ON t.store_id = s.store_id;
GO

-- ----------------------------------------------------------------------------
-- 3. v_points_activity — Points timeline with member context
-- ----------------------------------------------------------------------------
CREATE OR ALTER VIEW semantic.v_points_activity AS
SELECT
    p.point_id,
    p.member_id,
    m.first_name + ' ' + m.last_name AS member_name,
    m.tier AS member_tier,
    p.activity_date,
    p.activity_type,
    p.points_amount,
    p.balance_after,
    p.source,
    p.reference_id,
    p.description,
    p.created_at
FROM mirrored.member_points p
JOIN mirrored.loyalty_members m ON p.member_id = m.member_id;
GO

-- ----------------------------------------------------------------------------
-- 4. v_coupon_activity — Coupon lifecycle with rule details
-- ----------------------------------------------------------------------------
CREATE OR ALTER VIEW semantic.v_coupon_activity AS
SELECT
    c.coupon_id,
    c.coupon_code,
    c.member_id,
    m.first_name + ' ' + m.last_name AS member_name,
    m.tier AS member_tier,
    cr.rule_name,
    cr.description AS rule_description,
    c.issued_date,
    c.expiry_date,
    c.status,
    c.redeemed_date,
    c.redeemed_transaction_id,
    c.discount_type,
    c.discount_value,
    c.source_system,
    cr.min_purchase,
    cr.target_tier,
    c.created_at
FROM mirrored.coupons c
JOIN mirrored.coupon_rules cr ON c.coupon_rule_id = cr.rule_id
LEFT JOIN mirrored.loyalty_members m ON c.member_id = m.member_id;
GO

-- ----------------------------------------------------------------------------
-- 5. v_store_performance — Store-level aggregated metrics
-- ----------------------------------------------------------------------------
CREATE OR ALTER VIEW semantic.v_store_performance AS
SELECT
    s.store_id,
    s.store_name,
    s.city,
    s.state,
    s.zip_code,
    s.region,
    s.store_type,
    s.opened_date,
    COALESCE(ta.total_transactions, 0) AS total_transactions,
    COALESCE(ta.purchase_count, 0) AS purchase_count,
    COALESCE(ta.return_count, 0) AS return_count,
    COALESCE(ta.total_revenue, 0) AS total_revenue,
    ta.avg_transaction_value,
    COALESCE(ta.unique_members, 0) AS unique_members,
    ta.first_transaction_date,
    ta.last_transaction_date
FROM mirrored.stores s
LEFT JOIN (
    SELECT
        store_id,
        COUNT(*) AS total_transactions,
        SUM(CASE WHEN transaction_type = 'purchase' THEN 1 ELSE 0 END) AS purchase_count,
        SUM(CASE WHEN transaction_type = 'return' THEN 1 ELSE 0 END) AS return_count,
        SUM(CASE WHEN transaction_type = 'purchase' THEN total ELSE 0 END) AS total_revenue,
        AVG(CASE WHEN transaction_type = 'purchase' THEN total END) AS avg_transaction_value,
        COUNT(DISTINCT member_id) AS unique_members,
        MIN(transaction_date) AS first_transaction_date,
        MAX(transaction_date) AS last_transaction_date
    FROM mirrored.transactions
    GROUP BY store_id
) ta ON s.store_id = ta.store_id;
GO

-- ----------------------------------------------------------------------------
-- 6. v_product_popularity — Product/SKU performance metrics
-- ----------------------------------------------------------------------------
CREATE OR ALTER VIEW semantic.v_product_popularity AS
SELECT
    sr.sku,
    sr.product_name,
    sr.category,
    sr.subcategory,
    sr.brand,
    sr.unit_price AS list_price,
    sr.is_bonus_eligible,
    sr.is_skip_sku,
    COALESCE(ti.units_sold, 0) AS units_sold,
    COALESCE(ti.total_revenue, 0) AS total_revenue,
    COALESCE(ti.units_returned, 0) AS units_returned,
    CASE
        WHEN COALESCE(ti.units_sold, 0) = 0 THEN 0
        ELSE CAST(ti.units_returned AS FLOAT) / ti.units_sold * 100
    END AS return_rate_pct,
    COALESCE(ti.transaction_count, 0) AS transaction_count,
    COALESCE(ti.unique_buyers, 0) AS unique_buyers
FROM mirrored.sku_reference sr
LEFT JOIN (
    SELECT
        i.sku,
        SUM(CASE WHEN i.is_return = false THEN i.quantity ELSE 0 END) AS units_sold,
        SUM(CASE WHEN i.is_return = false THEN i.line_total ELSE 0 END) AS total_revenue,
        SUM(CASE WHEN i.is_return = true THEN i.quantity ELSE 0 END) AS units_returned,
        COUNT(DISTINCT i.transaction_id) AS transaction_count,
        COUNT(DISTINCT t.member_id) AS unique_buyers
    FROM mirrored.transaction_items i
    JOIN mirrored.transactions t ON i.transaction_id = t.transaction_id
    GROUP BY i.sku
) ti ON sr.sku = ti.sku;
GO

-- ----------------------------------------------------------------------------
-- 7. v_member_engagement — Member activity and behavior metrics
-- ----------------------------------------------------------------------------
CREATE OR ALTER VIEW semantic.v_member_engagement AS
SELECT
    m.member_id,
    m.first_name + ' ' + m.last_name AS full_name,
    m.tier,
    m.member_status,
    m.enrollment_date,
    COALESCE(ta.transaction_count, 0) AS transaction_count,
    ta.total_spend,
    ta.avg_spend_per_transaction,
    ta.last_purchase_date,
    DATEDIFF(day, ta.last_purchase_date, GETDATE()) AS days_since_last_purchase,
    COALESCE(pa.total_points_earned, 0) AS total_points_earned,
    COALESCE(pa.total_points_redeemed, 0) AS total_points_redeemed,
    COALESCE(pa.points_balance, 0) AS points_balance,
    CASE
        WHEN COALESCE(ta.total_spend, 0) = 0 THEN 0
        ELSE CAST(pa.total_points_earned AS FLOAT) / ta.total_spend
    END AS points_earn_rate,
    COALESCE(ca.coupons_issued, 0) AS coupons_issued,
    COALESCE(ca.coupons_redeemed, 0) AS coupons_redeemed,
    CASE
        WHEN COALESCE(ca.coupons_issued, 0) = 0 THEN 0
        ELSE CAST(ca.coupons_redeemed AS FLOAT) / ca.coupons_issued * 100
    END AS coupon_redemption_rate_pct,
    ta.preferred_channel
FROM mirrored.loyalty_members m
LEFT JOIN (
    SELECT
        member_id,
        COUNT(*) AS transaction_count,
        SUM(CASE WHEN transaction_type = 'purchase' THEN total ELSE 0 END) AS total_spend,
        AVG(CASE WHEN transaction_type = 'purchase' THEN total END) AS avg_spend_per_transaction,
        MAX(transaction_date) AS last_purchase_date,
        (SELECT TOP 1 channel FROM mirrored.transactions t2
         WHERE t2.member_id = t.member_id
         GROUP BY channel ORDER BY COUNT(*) DESC) AS preferred_channel
    FROM mirrored.transactions t
    GROUP BY member_id
) ta ON m.member_id = ta.member_id
LEFT JOIN (
    SELECT
        member_id,
        SUM(CASE WHEN points_amount > 0 THEN points_amount ELSE 0 END) AS total_points_earned,
        SUM(CASE WHEN points_amount < 0 THEN ABS(points_amount) ELSE 0 END) AS total_points_redeemed,
        SUM(points_amount) AS points_balance
    FROM mirrored.member_points
    GROUP BY member_id
) pa ON m.member_id = pa.member_id
LEFT JOIN (
    SELECT
        member_id,
        COUNT(*) AS coupons_issued,
        SUM(CASE WHEN status = 'redeemed' THEN 1 ELSE 0 END) AS coupons_redeemed
    FROM mirrored.coupons
    GROUP BY member_id
) ca ON m.member_id = ca.member_id;
GO

-- ----------------------------------------------------------------------------
-- 8. v_campaign_effectiveness — Coupon rule performance metrics
-- ----------------------------------------------------------------------------
CREATE OR ALTER VIEW semantic.v_campaign_effectiveness AS
SELECT
    cr.rule_id,
    cr.rule_name,
    cr.description,
    cr.discount_type,
    cr.discount_value,
    cr.min_purchase,
    cr.valid_days,
    cr.is_active,
    cr.target_tier,
    COALESCE(cs.total_issued, 0) AS total_issued,
    COALESCE(cs.total_redeemed, 0) AS total_redeemed,
    COALESCE(cs.total_expired, 0) AS total_expired,
    COALESCE(cs.total_voided, 0) AS total_voided,
    CASE
        WHEN COALESCE(cs.total_issued, 0) = 0 THEN 0
        ELSE CAST(cs.total_redeemed AS FLOAT) / cs.total_issued * 100
    END AS redemption_rate_pct,
    COALESCE(cs.revenue_from_redeemed, 0) AS revenue_from_redeemed_transactions,
    cs.avg_transaction_value_at_redemption,
    cr.created_at
FROM mirrored.coupon_rules cr
LEFT JOIN (
    SELECT
        c.coupon_rule_id,
        COUNT(*) AS total_issued,
        SUM(CASE WHEN c.status = 'redeemed' THEN 1 ELSE 0 END) AS total_redeemed,
        SUM(CASE WHEN c.status = 'expired' THEN 1 ELSE 0 END) AS total_expired,
        SUM(CASE WHEN c.status = 'voided' THEN 1 ELSE 0 END) AS total_voided,
        SUM(CASE WHEN c.status = 'redeemed' THEN t.total ELSE 0 END) AS revenue_from_redeemed,
        AVG(CASE WHEN c.status = 'redeemed' THEN t.total END) AS avg_transaction_value_at_redemption
    FROM mirrored.coupons c
    LEFT JOIN mirrored.transactions t ON c.redeemed_transaction_id = t.transaction_id
    GROUP BY c.coupon_rule_id
) cs ON cr.rule_id = cs.coupon_rule_id;
GO

-- ----------------------------------------------------------------------------
-- 9. v_audit_trail — Agent activity with member context
-- ----------------------------------------------------------------------------
CREATE OR ALTER VIEW semantic.v_audit_trail AS
SELECT
    aa.activity_id,
    aa.agent_id,
    a.agent_name,
    a.department AS agent_department,
    aa.member_id,
    m.first_name + ' ' + m.last_name AS member_name,
    m.tier AS member_tier,
    aa.activity_type,
    aa.activity_date,
    aa.details,
    aa.created_at
FROM mirrored.agent_activities aa
JOIN mirrored.agents a ON aa.agent_id = a.agent_id
JOIN mirrored.loyalty_members m ON aa.member_id = m.member_id;
GO

-- ============================================================================
-- Verification: Count rows in each view
-- ============================================================================
-- Run these after creating views to verify:
-- SELECT 'v_member_summary' AS view_name, COUNT(*) AS row_count FROM semantic.v_member_summary
-- UNION ALL SELECT 'v_transaction_history', COUNT(*) FROM semantic.v_transaction_history
-- UNION ALL SELECT 'v_transaction_history', COUNT(*) FROM semantic.v_points_activity
-- UNION ALL SELECT 'v_coupon_activity', COUNT(*) FROM semantic.v_coupon_activity
-- UNION ALL SELECT 'v_store_performance', COUNT(*) FROM semantic.v_store_performance
-- UNION ALL SELECT 'v_product_popularity', COUNT(*) FROM semantic.v_product_popularity
-- UNION ALL SELECT 'v_member_engagement', COUNT(*) FROM semantic.v_member_engagement
-- UNION ALL SELECT 'v_campaign_effectiveness', COUNT(*) FROM semantic.v_campaign_effectiveness
-- UNION ALL SELECT 'v_audit_trail', COUNT(*) FROM semantic.v_audit_trail;
