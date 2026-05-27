USE passwddb;
CREATE TABLE IF NOT EXISTS userlog (
    id INT AUTO_INCREMENT PRIMARY KEY,
    `index` INT DEFAULT NULL,
    `date` DATETIME NOT NULL,
    age INT,
    lev INT,
    passflag INT,
    runt_sec INT
);