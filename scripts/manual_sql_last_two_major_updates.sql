-- Manual patch for the last two major Lifecycle updates.
-- Generated from migration intent in:
--   migrations/versions/20260511_05_create_permission_tables.py
--   migrations/versions/20260521_01_add_inventory_tracking_mode_and_quantity.py
--
-- IMPORTANT:
-- 1) Run on PostgreSQL only.
-- 2) Review before execution.
-- 3) Do NOT modify shared `users` table.
-- 4) If your alembic_version currently has 20260511_04 and 20260510_02 branch state,
--    this script advances them to 20260511_05 and 20260521_01 respectively.

BEGIN;

-- === Update A: 20260511_05 (permissions tables branch) ===
CREATE TABLE IF NOT EXISTS distribution_lists (
  id INTEGER PRIMARY KEY,
  name VARCHAR(128) NOT NULL,
  email VARCHAR(255) NOT NULL,
  description VARCHAR(255),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT uq_distribution_lists_name UNIQUE (name),
  CONSTRAINT uq_distribution_lists_email UNIQUE (email)
);

CREATE TABLE IF NOT EXISTS file_share_permissions (
  id INTEGER PRIMARY KEY,
  name VARCHAR(128) NOT NULL,
  resource_path VARCHAR(512) NOT NULL,
  access_level VARCHAR(64),
  description VARCHAR(255),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT uq_file_share_permissions_name UNIQUE (name),
  CONSTRAINT uq_file_share_permissions_resource_path UNIQUE (resource_path)
);

CREATE TABLE IF NOT EXISTS role_distribution_lists (
  role_matrix_id INTEGER NOT NULL,
  distribution_list_id INTEGER NOT NULL,
  PRIMARY KEY (role_matrix_id, distribution_list_id),
  CONSTRAINT fk_role_distribution_lists_role_matrix_id
    FOREIGN KEY (role_matrix_id) REFERENCES role_matrix(id),
  CONSTRAINT fk_role_distribution_lists_distribution_list_id
    FOREIGN KEY (distribution_list_id) REFERENCES distribution_lists(id)
);

CREATE TABLE IF NOT EXISTS role_file_share_permissions (
  role_matrix_id INTEGER NOT NULL,
  file_share_permission_id INTEGER NOT NULL,
  PRIMARY KEY (role_matrix_id, file_share_permission_id),
  CONSTRAINT fk_role_file_share_permissions_role_matrix_id
    FOREIGN KEY (role_matrix_id) REFERENCES role_matrix(id),
  CONSTRAINT fk_role_file_share_permissions_file_share_permission_id
    FOREIGN KEY (file_share_permission_id) REFERENCES file_share_permissions(id)
);

CREATE INDEX IF NOT EXISTS ix_role_distribution_lists_distribution_list_id
  ON role_distribution_lists (distribution_list_id);
CREATE INDEX IF NOT EXISTS ix_role_file_share_permissions_file_share_permission_id
  ON role_file_share_permissions (file_share_permission_id);

-- Advance branch revision row if present.
UPDATE alembic_version
SET version_num = '20260511_05'
WHERE version_num = '20260511_04';

-- If row does not yet exist for this branch, insert it.
INSERT INTO alembic_version(version_num)
SELECT '20260511_05'
WHERE NOT EXISTS (SELECT 1 FROM alembic_version WHERE version_num = '20260511_05');


-- === Update B: 20260521_01 (inventory tracking mode + quantity branch) ===
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'asset_tracking_mode') THEN
    CREATE TYPE asset_tracking_mode AS ENUM ('Serialized', 'Quantity');
  END IF;
END$$;

ALTER TABLE inventory
  ADD COLUMN IF NOT EXISTS tracking_mode asset_tracking_mode NOT NULL DEFAULT 'Serialized';

ALTER TABLE inventory
  ADD COLUMN IF NOT EXISTS quantity INTEGER NOT NULL DEFAULT 1;

-- Advance branch revision row if present.
UPDATE alembic_version
SET version_num = '20260521_01'
WHERE version_num = '20260510_02';

-- If row does not yet exist for this branch, insert it.
INSERT INTO alembic_version(version_num)
SELECT '20260521_01'
WHERE NOT EXISTS (SELECT 1 FROM alembic_version WHERE version_num = '20260521_01');

COMMIT;
