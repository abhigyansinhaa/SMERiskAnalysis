-- Cashflow Risk Advisor - MySQL schema
-- Run as MySQL root or with appropriate privileges

CREATE DATABASE IF NOT EXISTS cashflow_risk
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE cashflow_risk;

-- Users
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_users_email (email)
);

-- Categories (income/expense)
CREATE TABLE IF NOT EXISTS categories (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  name VARCHAR(100) NOT NULL,
  type ENUM('income', 'expense') NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX ix_categories_user_type (user_id, type)
);

-- Transactions
CREATE TABLE IF NOT EXISTS transactions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  date DATE NOT NULL,
  amount DOUBLE NOT NULL,
  type ENUM('income', 'expense') NOT NULL,
  category_id INT NULL,
  merchant VARCHAR(255) NULL,
  notes TEXT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
  INDEX ix_transactions_user_date (user_id, date),
  INDEX ix_transactions_date (date)
);

-- Budgets
CREATE TABLE IF NOT EXISTS budgets (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  category_id INT NULL,
  month DATE NOT NULL,
  amount DOUBLE NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
  INDEX ix_budgets_user_month (user_id, month)
);

-- Forecasts
CREATE TABLE IF NOT EXISTS forecasts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  horizon_days INT NOT NULL,
  as_of_date DATE NOT NULL,
  predicted_net DOUBLE NOT NULL,
  predicted_balance DOUBLE NOT NULL,
  model_name VARCHAR(50) NOT NULL,
  metrics_json TEXT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Alerts
CREATE TABLE IF NOT EXISTS alerts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  kind VARCHAR(50) NOT NULL,
  severity ENUM('info', 'warning', 'critical') NOT NULL,
  message TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  is_read BOOLEAN DEFAULT FALSE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX ix_alerts_user_created (user_id, created_at)
);
