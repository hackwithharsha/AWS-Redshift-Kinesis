# Real-Time Ecommerce Analytics using `AWS Redshift` and `AWS Kinesis Data Stream`

> **Scenario :** We'll stream customer shopping events (`page views`, `add-to-cart`, `purchases`) to Kinesis, then we will use Redshift to analyze the data in real-time for business insights. To simulate this, we will create a python script to generate `fake` data.

### Architecture

- Python application publishes e-commerce events to Kinesis Data Stream.
- Redshift consumes data directly from Kinesis using `materialized views auto refresh from kinesis data source`.
- Analytics can be run on this continuously updated data.

> [!WARNING]
> Please create a budget alert for your AWS account to avoid unexpected charges. This project uses multiple AWS services, and costs can accumulate quickly if not monitored.

> [!IMPORTANT]
> This project is for educational purposes only. Please do not use it in production without proper testing and validation. As it doesn't cover edge cases or best practices for production use. In real-time, things will change based on `Non-Functional requirements`.

---

### Create `AWS Kinesis Data Stream`

```bash
>>> aws kinesis create-stream --stream-name ecommerce-events --shard-count 1
```

### Create `AWS Redshift Cluster`

```bash
>>> aws redshift create-cluster \
    --cluster-identifier ecommerce-analytics \
    --node-type dc2.large \
    --number-of-nodes 2 \
    --master-username admin \
    --master-user-password testPassword123 \
    --db-name ecommerce
```

Create default vpc if required

```bash
>>> aws ec2 create-default-vpc
```

### Configure `Redshift to access Kinesis`

> [!IMPORTANT]
> Try to understand `trust-policy.json` file. Here, we are attaching this role to `Redshift`. so that, only `Redshift` can assume this role.

```bash
>>> aws iam create-role \
  --role-name RedshiftKinesisRole \
  --assume-role-policy-document file://trust-policy.json \
  --description "IAM Role for AWS Redshift to access Kinesis Data Stream"
```

Attach AWS Managed `AmazonKinesisReadOnlyAccess` Policy to the newly created role. This will allow Redshift interact with `Kinesis Data Stream`.

```bash
>>> aws iam attach-role-policy --role-name RedshiftKinesisRole --policy-arn arn:aws:iam::aws:policy/AmazonKinesisReadOnlyAccess
```

Attach the IAM role to our Redshift cluster, Replace `<YOUR-ACCOUNT-ID>` with your actual AWS account ID.

```bash
>>> aws redshift modify-cluster-iam-roles \
    --cluster-identifier ecommerce-analytics \
    --add-iam-roles arn:aws:iam::<YOUR-ACCOUNT-ID>:role/RedshiftKinesisRole
```

### Create `Materialized View` in Redshift

```sql
-- This is to organize the database objects like materialized view. example `events_realtime`
CREATE SCHEMA ecommerce;
```

```sql
-- Create external schema for Kinesis
CREATE EXTERNAL SCHEMA kinesis_schema
FROM KINESIS
IAM_ROLE 'arn:aws:iam::<YOUR-ACCOUNT-ID>:role/RedshiftKinesisRole';
```

> [!NOTE]
> In the `FROM` clause of Materialized View, we need to mention Kinesis stream name, In this example, we are using `ecommerce-events` as stream name that's what we created in the beginning.

```sql
CREATE MATERIALIZED VIEW ecommerce.events_realtime AUTO REFRESH YES
AS
SELECT 
    JSON_EXTRACT_PATH_TEXT(FROM_VARBYTE(kinesis_data, 'utf-8'), 'event_id') AS event_id,
    JSON_EXTRACT_PATH_TEXT(FROM_VARBYTE(kinesis_data, 'utf-8'), 'event_type') AS event_type,
    JSON_EXTRACT_PATH_TEXT(FROM_VARBYTE(kinesis_data, 'utf-8'), 'user_id') AS user_id,
    JSON_EXTRACT_PATH_TEXT(FROM_VARBYTE(kinesis_data, 'utf-8'), 'product_id') AS product_id,
    TIMESTAMP 'epoch' + JSON_EXTRACT_PATH_TEXT(FROM_VARBYTE(kinesis_data, 'utf-8'), 'timestamp')::DECIMAL(15, 3) * INTERVAL '1 second' AS timestamp,
    JSON_EXTRACT_PATH_TEXT(FROM_VARBYTE(kinesis_data, 'utf-8'), 'session_id') AS session_id,
    JSON_EXTRACT_PATH_TEXT(FROM_VARBYTE(kinesis_data, 'utf-8'), 'price')::DECIMAL(10, 2) AS price,
    JSON_EXTRACT_PATH_TEXT(FROM_VARBYTE(kinesis_data, 'utf-8'), 'quantity')::INTEGER AS quantity,
    JSON_EXTRACT_PATH_TEXT(FROM_VARBYTE(kinesis_data, 'utf-8'), 'user_agent') AS user_agent,
    JSON_EXTRACT_PATH_TEXT(FROM_VARBYTE(kinesis_data, 'utf-8'), 'page_url') AS page_url,
    JSON_EXTRACT_PATH_TEXT(FROM_VARBYTE(kinesis_data, 'utf-8'), 'ip_address') AS ip_address
FROM kinesis_schema."ecommerce-events"
WHERE CAN_JSON_PARSE(kinesis_data);
```

### Send Sample `Events` to `Kinesis Data Stream`

```bash
>>> python3 -m pip install -r requirements.txt
```

```bash
>>> python3 main.py
```

### Create `Analytical Queries` on the `Materialized View`

```sql
-- Real-time product popularity
SELECT 
    product_id,
    COUNT(*) as view_count
FROM ecommerce.events_realtime 
WHERE event_type = 'page_view'
AND timestamp > DATEADD(hour, -1, GETDATE())
GROUP BY product_id
ORDER BY view_count DESC
LIMIT 10;
```

```sql
-- Conversion funnel analysis
SELECT 
    event_type,
    COUNT(DISTINCT user_id) as user_count
FROM ecommerce.events_realtime
WHERE timestamp > DATEADD(day, -1, GETDATE())
GROUP BY event_type;
```

```sql
-- Revenue in the last hour
SELECT 
    SUM(price * quantity) as revenue_last_hour
FROM ecommerce.events_realtime
WHERE event_type = 'purchase'
AND timestamp > DATEADD(hour, -1, GETDATE());
```

## Cleanup

**Delete the Redshift Cluster**

```bash
>>> aws redshift delete-cluster \
    --cluster-identifier ecommerce-analytics \
    --skip-final-cluster-snapshot
```

**Delete the Kinesis Data Stream**

```bash
>>> aws kinesis delete-stream --stream-name ecommerce-events
```

**Detach policy from role**

```bash
>>> aws iam detach-role-policy \
    --role-name RedshiftKinesisRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonKinesisReadOnlyAccess
```

**Delete the role**

```bash
>>> aws iam delete-role --role-name RedshiftKinesisRole
```

**Delete the s3 bucket**

```bash
>>> aws s3 rm s3://hack-with-harsha/ --recursive
```

```bash
>>> aws s3 rb s3://hack-with-harsha --force
```