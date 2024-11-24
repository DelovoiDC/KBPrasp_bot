CREATE TABLE ej_average_data (
    `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `chat_id` VARCHAR(20) NOT NULL,
    `name` VARCHAR(20) NOT NULL,
    `mark` VARCHAR(3) NOT NULL,
    FOREIGN KEY (`chat_id`) REFERENCES `users` (`chat_id`)
);
