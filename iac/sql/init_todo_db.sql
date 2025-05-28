-- Init script for Django todo list database
-- This SQL initializes the tables and permissions needed for the Django todo application

-- Check if pgvector extension is available
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_available_extensions WHERE name = 'pgvector'
    ) THEN
        EXECUTE 'CREATE EXTENSION IF NOT EXISTS pgvector';
    ELSE
        RAISE NOTICE 'pgvector extension is not available on this RDS instance. Vector operations will not be available.';
    END IF;
END $$;

-- Create user table if Django's auth will be used
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_catalog.pg_tables
        WHERE schemaname = 'public'
        AND tablename = 'auth_user'
    ) THEN
        RAISE NOTICE 'Django auth_user table will be created by Django migrations';
    END IF;
END $$;

-- Create todos table if Django migrations haven't run yet
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_catalog.pg_tables
        WHERE schemaname = 'public'
        AND tablename = 'todo_app_todo'
    ) THEN
        CREATE TABLE todo_app_todo (
            id UUID PRIMARY KEY,
            title VARCHAR(100) NOT NULL,
            description TEXT,
            completed BOOLEAN NOT NULL DEFAULT FALSE,
            due_date TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        -- Indexes
        CREATE INDEX idx_todo_app_todo_completed ON todo_app_todo(completed);
        CREATE INDEX idx_todo_app_todo_due_date ON todo_app_todo(due_date);
        
        -- Insert sample data
        INSERT INTO todo_app_todo (id, title, description, completed, due_date)
        VALUES 
            (gen_random_uuid(), 'Set up Aurora database', 'Configure and deploy Aurora PostgreSQL', TRUE, CURRENT_TIMESTAMP - INTERVAL '2 day'),
            (gen_random_uuid(), 'Create Django todo app', 'Implement RESTful API endpoints for todo management', TRUE, CURRENT_TIMESTAMP - INTERVAL '1 day'),
            (gen_random_uuid(), 'Test database connectivity', 'Verify the Django application can connect to Aurora DB', FALSE, CURRENT_TIMESTAMP + INTERVAL '1 day'),
            (gen_random_uuid(), 'Deploy to production', 'Deploy the Django todo list application to production environment', FALSE, CURRENT_TIMESTAMP + INTERVAL '7 day');
    ELSE
        RAISE NOTICE 'Django todo_app_todo table already exists';
    END IF;
END $$;

-- Grant permissions
DO $$ 
BEGIN
    EXECUTE format('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO %I', current_user);
    EXECUTE format('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO %I', current_user);
END $$;

-- Create function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for the todo_app_todo table if it exists
DO $$ 
BEGIN
    IF EXISTS (
        SELECT FROM pg_catalog.pg_tables
        WHERE schemaname = 'public'
        AND tablename = 'todo_app_todo'
    ) AND NOT EXISTS (
        SELECT FROM pg_trigger
        WHERE tgname = 'update_todo_app_todo_updated_at'
    ) THEN
        CREATE TRIGGER update_todo_app_todo_updated_at
        BEFORE UPDATE ON todo_app_todo
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Add permissions for pgvector
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO PUBLIC;