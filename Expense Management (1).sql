-- ==============================
-- Expense Management DB Setup
-- ==============================
DROP DATABASE IF EXISTS expense_management;
CREATE DATABASE expense_management;
USE expense_management;

CREATE TABLE Company (
    company_id INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(100) NOT NULL,
    base_currency VARCHAR(10) NOT NULL
);

CREATE TABLE Users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL,
    role ENUM('Admin','Manager','Employee') NOT NULL,
    manager_id INT NULL,
    company_id INT NOT NULL,
    FOREIGN KEY (company_id) REFERENCES Company(company_id)
);

CREATE TABLE Expenses (
    expense_id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(10) NOT NULL,
    category VARCHAR(50),
    description TEXT,
    expense_date DATE NOT NULL,
    status ENUM('Pending','Approved','Rejected') DEFAULT 'Pending',
    FOREIGN KEY (employee_id) REFERENCES Users(user_id)
);

CREATE TABLE Approvals (
    approval_id INT AUTO_INCREMENT PRIMARY KEY,
    expense_id INT NOT NULL,
    approver_id INT NOT NULL,
    decision ENUM('Pending','Approved','Rejected') DEFAULT 'Pending',
    comments TEXT,
    step_order INT NOT NULL,
    decided_at TIMESTAMP NULL,
    FOREIGN KEY (expense_id) REFERENCES Expenses(expense_id),
    FOREIGN KEY (approver_id) REFERENCES Users(user_id)
);

CREATE TABLE ApprovalRules (
    rule_id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    rule_type ENUM('Percentage','Specific','Hybrid') NOT NULL,
    threshold_value DECIMAL(5,2) NULL,
    specific_approver_id INT NULL,
    FOREIGN KEY (company_id) REFERENCES Company(company_id),
    FOREIGN KEY (specific_approver_id) REFERENCES Users(user_id)
);

INSERT INTO Company (company_name, base_currency) 
VALUES ('TechCorp', 'INR');

INSERT INTO Users (username, password, role, manager_id, company_id)
VALUES 
('admin1', 'admin123', 'Admin', NULL, 1),
('manager1', 'mgr123', 'Manager', NULL, 1),
('emp1', 'emp123', 'Employee', 2, 1),
('emp2', 'emp456', 'Employee', 2, 1);

INSERT INTO Expenses (employee_id, amount, currency, category, description, expense_date, status)
VALUES
(3, 1200, 'USD', 'Travel', 'Flight to Bangalore', '2025-10-01', 'Pending'),
(4, 500, 'INR', 'Food', 'Team lunch', '2025-10-02', 'Pending');

INSERT INTO Approvals (expense_id, approver_id, decision, step_order)
VALUES
(1, 2, 'Pending', 1),
(2, 2, 'Pending', 1);

INSERT INTO ApprovalRules (company_id, rule_type, threshold_value, specific_approver_id)
VALUES
(1, 'Percentage', 60, NULL),
(1, 'Specific', NULL, 1);

SELECT * FROM Expenses WHERE employee_id=3;

SELECT a.approval_id, e.expense_id, e.amount, e.currency, e.category, e.description, e.status
FROM Approvals a
JOIN Expenses e ON a.expense_id = e.expense_id
WHERE a.approver_id = 2 AND a.decision = 'Pending';

UPDATE Approvals SET decision='Approved', comments='Looks valid', decided_at=NOW()
WHERE approval_id=1;

UPDATE Approvals SET decision='Rejected', comments='Not valid', decided_at=NOW()
WHERE approval_id=2;
UPDATE Expenses SET status='Rejected' WHERE expense_id=2;

SELECT 
    (SUM(CASE WHEN decision='Approved' THEN 1 ELSE 0 END) / COUNT(*)) * 100 AS approval_percentage
FROM Approvals
WHERE expense_id=1;
