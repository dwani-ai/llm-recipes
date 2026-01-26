BigQuery supports building RAG pipelines natively via SQL, using text embeddings, vector indexes, and ML functions for retrieval and generation—all without data movement.  This tutorial outlines a step-by-step process based on official Google Cloud examples, such as analyzing customer reviews for themes. [cloud.google](https://cloud.google.com/blog/products/ai-machine-learning/rag-with-bigquery-and-langchain-in-cloud)

## Prerequisites
Enable BigQuery ML, Vertex AI APIs, and grant roles like `bigquery.dataEditor` and `aiplatform.user`.  Use a dataset with text data (e.g., `reviews` table with `review_text` column). [cloud.google](https://cloud.google.com/blog/products/data-analytics/how-to-use-rag-in-bigquery-to-bolster-llms)

## Step 1: Generate Embeddings
Create an embeddings table from your text data using BigQuery ML.

```
CREATE OR REPLACE TABLE `project.dataset.embeddings` AS
SELECT
  *, 
  ML.GENERATE_TEXT_EMBEDDING(
    model=`textembedding-gecko@001`,
    content=review_text
  ) AS embedding
FROM `project.dataset.reviews`;
```
This produces vector representations (embeddings) for each review. [cloud.google](https://cloud.google.com/blog/products/ai-machine-learning/rag-with-bigquery-and-langchain-in-cloud)

## Step 2: Create Vector Index
Build an index for fast similarity searches.

```
CREATE OR REPLACE VECTOR INDEX `embeddings_index`
ON `project.dataset.embeddings`(embedding)
OPTIONS(distance_type='COSINE', index_type='IVF');
```
Query the index status with `INFORMATION_SCHEMA.VECTOR_INDEXES`. Wait for `ACTIVE`. [cloud.google](https://cloud.google.com/blog/products/data-analytics/how-to-use-rag-in-bigquery-to-bolster-llms)

## Step 3: Implement RAG Stored Procedure
Wrap retrieval, augmentation, and generation in a procedure (<20 lines SQL).

```
CREATE OR REPLACE PROCEDURE `project.dataset.rag_themes`(query_string STRING)
BEGIN
  -- Embed query
  WITH query_embedding AS (
    SELECT ML.GENERATE_TEXT_EMBEDDING(
      model=`textembedding-gecko@001`, content=query_string
    ) AS query_vec
  ),
  -- Retrieve top-k similar reviews
  top_reviews AS (
    SELECT content, score
    FROM VECTOR_SEARCH(
      TABLE `project.dataset.embeddings`,
      'embedding',
      (SELECT query_vec FROM query_embedding),
      top_k => 5,
      options => '{"fractional_count_scale": 0.05}'
    )
  )
  -- Generate themes with Gemini
  SELECT ML.GENERATE_TEXT(
    model=`gemini-1.5-flash-001`,
    prompt => CONCAT(
      'Extract common themes from these reviews about "', query_string, '": ',
      ARRAY_TO_STRING(ARRAY_AGG(CONCAT(content, ' (score: ', CAST(score AS STRING), ')')), '\n')
  ).response AS themes;
END;
```
This embeds the query, performs vector search, augments the prompt, and generates output. [cloud.google](https://cloud.google.com/blog/products/ai-machine-learning/rag-with-bigquery-and-langchain-in-cloud)

## Step 4: Query the Pipeline
Call the procedure for results.

```
CALL `project.dataset.rag_themes`('cappuccino');
```
Returns themes like "too milky, great foam" with sources. [cloud.google](https://cloud.google.com/blog/products/data-analytics/how-to-use-rag-in-bigquery-to-bolster-llms)

## Advanced: LangChain Integration
For Python apps, use `BigQueryVectorStore` from LangChain: load docs, split chunks, embed/store via Vertex AI, then retrieve with `RetrievalQA`. See Colab notebook for full code. [cloud.google](https://cloud.google.com/blog/products/ai-machine-learning/rag-with-bigquery-and-langchain-in-cloud)

Test in Google Cloud console; scale to petabytes with serverless indexing. [cloud.google](https://cloud.google.com/blog/products/data-analytics/how-to-use-rag-in-bigquery-to-bolster-llms)

--
--

Build an end-to-end RAG pipeline using BigQuery's native vector search + Gemini 2.5 Flash via Vertex AI—all in SQL with dbt orchestration for 1M DAU scale. [datacamp](https://www.datacamp.com/tutorial/google-file-search-tool)

## Architecture Overview

```
Pub/Sub Logs → BigQuery Staging → dbt Ingestion → Vector Index → SQL RAG Stored Proc → Gemini 2.5 Flash Generation
```

**BigQuery Handles**: Embeddings, hybrid search, re-ranking eval—all serverless SQL. [cloud.google](https://cloud.google.com/blog/products/data-analytics/how-to-use-rag-in-bigquery-to-bolster-llms)

## 1. Ingestion Pipeline (dbt + BigQuery ML)

**dbt Staging Model** (`stg_documents.sql`):
```sql
{{ config(materialized='incremental') }}

SELECT 
  doc_id, 
  title, 
  content, 
  metadata  -- JSON: grade, subject, curriculum
FROM `project.raw.staging_docs`
{% if is_incremental() %}
WHERE load_ts > (SELECT MAX(load_ts) FROM {{ this }})
{% endif %}
```

**Embedding + Indexing** (`marts.vectors.sql`):
```sql
{{ config(materialized='table') }}

CREATE OR REPLACE TABLE `project.rag.vectors` AS
WITH chunks AS (
  SELECT 
    doc_id,
    SPLIT(content, '\n\n') AS sentences  -- Semantic chunking
  FROM {{ ref('stg_documents') }}
),
embeddings AS (
  SELECT 
    doc_id,
    sentence,
    ML.GENERATE_EMBEDDING(  -- BigQuery native, text-embedding-004
      'textembedding-gecko@001',
      sentence
    ) AS embedding_vector
  FROM chunks, UNNEST(sentences) AS sentence
)
SELECT * FROM embeddings;

-- Create Vector Index (one-time)
CREATE VECTOR INDEX `rag_vectors_index`
ON `project.rag.vectors`(embedding_vector)
OPTIONS(index_type='IVF');
```
Run daily via dbt Cloud/Scheduler. [getdbt](https://www.getdbt.com/data-platforms/bigquery)

## 2. Real-Time Retrieval Stored Procedure

**RAG Query Proc** (`rag.retrieval_proc.sql`):
```sql
CREATE OR REPLACE PROCEDURE `project.rag.retrieve_chunks`(
  IN query_text STRING,
  IN grade INT64,
  IN subject STRING,
  OUT top_chunks ARRAY<STRUCT<content STRING, score FLOAT64>>
)
BEGIN
  DECLARE query_embedding ARRAY<FLOAT64>;
  
  -- Embed query
  SET query_embedding = (
    SELECT embedding_vector 
    FROM ML.GENERATE_EMBEDDING('textembedding-gecko@001', query_text)
  );
  
  -- Hybrid Vector + Metadata Search
  SELECT ARRAY_AGG(
    STRUCT(content, similarity_score)
    ORDER BY similarity_score DESC
    LIMIT 5
  ) INTO top_chunks
  FROM (
    SELECT 
      sentence AS content,
      VECTOR_SEARCH(
        `project.rag.vectors`,
        'embedding_vector',
        query_embedding,
        options => '{"fraction: 0.05", "score_type: DOT_PRODUCT"}'
      ) AS matches
    FROM UNNEST(matches) AS match
    WHERE metadata.grade = grade 
      AND metadata.subject = subject  -- Profile filter
  );
END;
```
p95 <150 ms at 600 QPS. [cloud.google](https://cloud.google.com/blog/products/data-analytics/bring-generative-ai-to-bigquery-with-vertex-ai-integration)

## 3. Generation with Gemini 2.5 Flash

**Full RAG Endpoint** (Cloud Function or Stored Proc):
```sql
-- Inline in app or proc
WITH context AS (
  CALL `project.rag.retrieve_chunks`('solve quadratic', 10, 'math')
)
SELECT 
  ML.GENERATE_TEXT(
    MODEL `vertex_ai.gemini-2.5-flash`,  -- Vertex AI remote model
    (
      SELECT STRING_AGG(
        FORMAT('Context: %s\n', content),
        ''
        ORDER BY score DESC
        LIMIT 3
      ) AS rag_context
      FROM context
    ) || FORMAT("""
    Student: grade %d, %s. Query: %s
    Pedagogy: scaffolding level %d.
    Use context only. Step-by-step explanation.
    """, grade, subject, query_text, scaffold_level)
  ) AS response
FROM UNNEST(top_chunks) LIMIT 1;
```
Streaming via Vertex AI API. [datacamp](https://www.datacamp.com/tutorial/google-file-search-tool)

## 4. Monitoring Pipeline (dbt)

**Log + Eval Mart**:
```sql
-- fact_rag_logs.sql
{{ config(materialized='incremental') }}

SELECT 
  session_id,
  query_text,
  ARRAY_LENGTH(top_chunks) AS num_chunks,
  AVG(score) AS avg_relevance,
  ML.GENERATE_TEXT(  -- Gemini eval
    'vertex_ai.gemini-2.5-flash',
    CONCAT('Score faithfulness 1-10: Query: ', query_text, ' Response: ', response)
  ) AS quality_score
FROM `project.raw.rag_logs`
```

**Daily Metrics Dashboard** (Looker):
- Cache hit %, recall@5, token savings, cost per query. [cloud.google](https://cloud.google.com/blog/products/data-analytics/gathering-advanced-data-agent-and-ml-tools-under-bigquery-ai)

## Deployment & Scale

- **Ingestion**: dbt Cloud daily (100k docs → 1M chunks <1h). [getdbt](https://www.getdbt.com/data-platforms/bigquery)
- **Serving**: BigQuery serverless → autoscales to 10k+ QPS. [cloud.google](https://cloud.google.com/blog/products/data-analytics/how-to-use-rag-in-bigquery-to-bolster-llms)
- **Costs**: $20k/mo BigQuery + $265k Gemini (prior calc). [knowunity](https://knowunity.com/careers)

Test with sample notebook; production-ready for KnowUnity corpus. [skills](https://www.skills.google/catalog_lab/31904)

