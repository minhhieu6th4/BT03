CREATE TABLE competitions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    status ENUM('PENDING', 'RUNNING', 'COMPLETED') DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE teams (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE submissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    team_id INT NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    status ENUM('PENDING', 'VALIDATING', 'VALID', 'INVALID') DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(id)
);

CREATE TABLE rounds (
    id INT AUTO_INCREMENT PRIMARY KEY,
    competition_id INT NOT NULL,
    name VARCHAR(50) NOT NULL, -- e.g., 'QUALIFICATION', 'ROUND_OF_32'
    type ENUM('ROUND_ROBIN', 'KNOCKOUT') NOT NULL,
    FOREIGN KEY (competition_id) REFERENCES competitions(id)
);

CREATE TABLE groups_table (
    id INT AUTO_INCREMENT PRIMARY KEY,
    round_id INT NOT NULL,
    name VARCHAR(50) NOT NULL,
    FOREIGN KEY (round_id) REFERENCES rounds(id)
);

CREATE TABLE group_standings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id INT NOT NULL,
    team_id INT NOT NULL,
    points INT DEFAULT 0,
    wins INT DEFAULT 0,
    draws INT DEFAULT 0,
    losses INT DEFAULT 0,
    FOREIGN KEY (group_id) REFERENCES groups_table(id),
    FOREIGN KEY (team_id) REFERENCES teams(id)
);

CREATE TABLE matches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id INT, -- NULL nếu đấu loại trực tiếp
    round_id INT NOT NULL,
    team_a_id INT NOT NULL,
    team_b_id INT NOT NULL,
    format ENUM('BO1', 'BO3', 'BO5', 'BO7') DEFAULT 'BO1',
    status ENUM('PENDING', 'RUNNING', 'COMPLETED') DEFAULT 'PENDING',
    winner_id INT,
    FOREIGN KEY (group_id) REFERENCES groups_table(id),
    FOREIGN KEY (round_id) REFERENCES rounds(id),
    FOREIGN KEY (team_a_id) REFERENCES teams(id),
    FOREIGN KEY (team_b_id) REFERENCES teams(id),
    FOREIGN KEY (winner_id) REFERENCES teams(id)
);

CREATE TABLE games (
    id INT AUTO_INCREMENT PRIMARY KEY,
    match_id INT NOT NULL,
    game_number INT NOT NULL,
    team_red_id INT NOT NULL,
    team_blue_id INT NOT NULL,
    status ENUM('PENDING', 'COMPLETED') DEFAULT 'PENDING',
    winner_id INT,
    reason VARCHAR(255),
    log_file_path VARCHAR(255), -- Đường dẫn tới file match.json
    FOREIGN KEY (match_id) REFERENCES matches(id),
    FOREIGN KEY (team_red_id) REFERENCES teams(id),
    FOREIGN KEY (team_blue_id) REFERENCES teams(id)
);
