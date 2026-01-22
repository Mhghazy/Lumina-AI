-- ========================================
-- SUPABASE SETUP FOR DIRECT COLUMN CREATION
-- ========================================
-- Copy this entire file and paste it into:
-- Supabase Dashboard > SQL Editor > New Query > Run
-- ========================================

-- Function 1: Execute any SQL (most flexible)
CREATE OR REPLACE FUNCTION execute_sql(sql_query text)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  EXECUTE sql_query;
  RETURN json_build_object('success', true, 'message', 'Query executed successfully');
EXCEPTION 
  WHEN OTHERS THEN
    RETURN json_build_object('success', false, 'error', SQLERRM, 'detail', SQLSTATE);
END;
$$;

GRANT EXECUTE ON FUNCTION execute_sql(text) TO anon, authenticated;

-- Function 2: Add column (safer, validated)
CREATE OR REPLACE FUNCTION add_table_column(
  table_name text,
  column_name text,
  column_type text,
  default_value text DEFAULT NULL,
  is_nullable boolean DEFAULT true
)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  sql_statement text;
BEGIN
  -- Build ALTER TABLE statement
  sql_statement := format('ALTER TABLE %I ADD COLUMN IF NOT EXISTS %I %s', table_name, column_name, column_type);
  
  IF default_value IS NOT NULL THEN
    sql_statement := sql_statement || format(' DEFAULT %L', default_value);
  END IF;
  
  IF NOT is_nullable THEN
    sql_statement := sql_statement || ' NOT NULL';
  END IF;
  
  EXECUTE sql_statement;
  
  RETURN json_build_object('success', true, 'message', format('Column %s added', column_name), 'sql', sql_statement);
EXCEPTION 
  WHEN OTHERS THEN
    RETURN json_build_object('success', false, 'error', SQLERRM);
END;
$$;

GRANT EXECUTE ON FUNCTION add_table_column(text, text, text, text, boolean) TO anon, authenticated;

-- Function 3: Drop column
CREATE OR REPLACE FUNCTION drop_table_column(table_name text, column_name text)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  EXECUTE format('ALTER TABLE %I DROP COLUMN IF EXISTS %I', table_name, column_name);
  RETURN json_build_object('success', true, 'message', format('Column %s removed', column_name));
EXCEPTION 
  WHEN OTHERS THEN
    RETURN json_build_object('success', false, 'error', SQLERRM);
END;
$$;

GRANT EXECUTE ON FUNCTION drop_table_column(text, text) TO anon, authenticated;

-- Function 4: Rename column
CREATE OR REPLACE FUNCTION rename_table_column(table_name text, old_column_name text, new_column_name text)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  EXECUTE format('ALTER TABLE %I RENAME COLUMN %I TO %I', table_name, old_column_name, new_column_name);
  RETURN json_build_object('success', true, 'message', format('Column renamed from %s to %s', old_column_name, new_column_name));
EXCEPTION 
  WHEN OTHERS THEN
    RETURN json_build_object('success', false, 'error', SQLERRM);
END;
$$;

GRANT EXECUTE ON FUNCTION rename_table_column(text, text, text) TO anon, authenticated;

-- ========================================
-- SETUP COMPLETE!
-- ========================================
-- After running this, go back to vendors.html
-- and try adding a column again.
-- It will now appear in Supabase automatically!
-- ========================================
