-- Run once as the MariaDB root user:  sudo mariadb < backend/setup_mariadb.sql
CREATE DATABASE IF NOT EXISTS musabe CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'musabe'@'localhost' IDENTIFIED BY 'change-me';
GRANT ALL PRIVILEGES ON musabe.* TO 'musabe'@'localhost';
FLUSH PRIVILEGES;
