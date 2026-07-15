-- Warehouse-style SQL (BigQuery Standard SQL) for the notebook's user-level table.
-- Assignment is anchored once per user; outcome windows are measured after exposure.

WITH assignment AS (
    SELECT
        user_id,
        experiment_group AS `group`,
        assigned_at AS exposure_ts,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY assigned_at) AS assignment_rank
    FROM `analytics.experiment_assignments`
    WHERE experiment_name = 'one_click_checkout_v1'
),
first_assignment AS (
    SELECT user_id, `group`, exposure_ts
    FROM assignment
    WHERE assignment_rank = 1
),
user_context AS (
    SELECT
        a.user_id,
        a.`group`,
        u.device_type,
        u.country,
        DATE(u.signup_ts) AS signup_date,
        DATE(a.exposure_ts) AS exposure_date,
        DATE_DIFF(DATE(a.exposure_ts), DATE(u.signup_ts), DAY) AS days_since_signup
    FROM first_assignment a
    JOIN `analytics.users` u USING (user_id)
),
sessions AS (
    SELECT
        a.user_id,
        COUNT(DISTINCT s.session_id) AS session_count
    FROM first_assignment a
    LEFT JOIN `analytics.sessions` s
      ON a.user_id = s.user_id
     AND s.session_start >= a.exposure_ts
     AND s.session_start < TIMESTAMP_ADD(a.exposure_ts, INTERVAL 28 DAY)
    GROUP BY 1
),
orders_ranked AS (
    SELECT
        a.user_id,
        o.order_id,
        o.net_revenue,
        o.is_refunded,
        ROW_NUMBER() OVER (PARTITION BY a.user_id ORDER BY o.order_ts) AS order_number_in_window
    FROM first_assignment a
    JOIN `analytics.orders` o
      ON a.user_id = o.user_id
     AND o.order_ts >= a.exposure_ts
     AND o.order_ts < TIMESTAMP_ADD(a.exposure_ts, INTERVAL 28 DAY)
),
order_outcomes AS (
    SELECT
        user_id,
        COUNT(DISTINCT order_id) > 0 AS converted,
        SUM(net_revenue) AS revenue,
        MAX(CAST(is_refunded AS INT64)) AS refund_rate,
        MIN(order_number_in_window) AS first_order_number
    FROM orders_ranked
    GROUP BY 1
),
user_level AS (
    SELECT
        c.user_id,
        c.`group`,
        c.device_type,
        c.country,
        c.signup_date,
        c.exposure_date,
        COALESCE(s.session_count, 0) AS session_count,
        COALESCE(o.converted, FALSE) AS converted,
        COALESCE(o.revenue, 0) AS revenue,
        c.days_since_signup,
        COALESCE(o.refund_rate, 0) AS refund_rate
    FROM user_context c
    LEFT JOIN sessions s USING (user_id)
    LEFT JOIN order_outcomes o USING (user_id)
)

SELECT
    `group`,
    COUNT(*) AS users,
    COUNTIF(converted) AS conversions,
    SAFE_DIVIDE(COUNTIF(converted), COUNT(*)) AS conversion_rate,
    AVG(revenue) AS revenue_per_user,
    SAFE_DIVIDE(SUM(refund_rate), COUNTIF(converted)) AS refund_rate_among_buyers
FROM user_level
GROUP BY 1
ORDER BY 1;

-- For notebook parity, replace the final SELECT with: SELECT * FROM user_level;

