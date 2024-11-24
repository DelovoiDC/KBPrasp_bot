CREATE TABLE ej_marks (
    `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `chat_id` VARCHAR(20) NOT NULL,
    `mark` VARCHAR(20) NOT NULL,
    `name` VARCHAR(20) NOT NULL,
    `month` VARCHAR(2) NOT NULL,
    `dat` VARCHAR(2) NOT NULL,
    `title` VARCHAR(100),
    FOREIGN KEY (`chat_id`) REFERENCES `users` (`chat_id`)
);
