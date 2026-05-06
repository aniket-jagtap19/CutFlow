-- ============================================================
-- CutFlow – MySQL Schema
-- Run this ONCE to bootstrap the database before migrations.
-- Usage:
--   mysql -u root -p < schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS cutflow_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'cutflow_user'@'localhost'
    IDENTIFIED BY 'your_password_here';

GRANT ALL PRIVILEGES ON cutflow_db.* TO 'cutflow_user'@'localhost';
FLUSH PRIVILEGES;

USE cutflow_db;

-- ── Django auth & session tables (created by migrate) ────────────────────────
-- Listed here for reference; Django's migrate command creates them automatically.

-- ── fabricator_project ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `fabricator_project` (
    `id`         BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `name`       VARCHAR(150) NOT NULL,
    `created_at` DATETIME(6)  NOT NULL,
    `updated_at` DATETIME(6)  NOT NULL,
    `user_id`    INT          NOT NULL,
    CONSTRAINT `fk_project_user`
        FOREIGN KEY (`user_id`)
        REFERENCES `auth_user` (`id`)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── fabricator_savedwindow ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `fabricator_savedwindow` (
    `id`         BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `code`       VARCHAR(50)  NOT NULL,
    `width`      DOUBLE       NOT NULL,
    `height`     DOUBLE       NOT NULL,
    `typology`   VARCHAR(50)  NOT NULL,
    `glass_type` VARCHAR(50)  NOT NULL,
    `finish`     VARCHAR(50)  NOT NULL,
    `mesh`       TINYINT(1)   NOT NULL DEFAULT 0,
    `qty`        INT          NOT NULL DEFAULT 1,
    `project_id` BIGINT       NOT NULL,
    CONSTRAINT `fk_savedwindow_project`
        FOREIGN KEY (`project_id`)
        REFERENCES `fabricator_project` (`id`)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
