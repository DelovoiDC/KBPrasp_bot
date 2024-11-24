CREATE TABLE rasp_entities (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `entity_id` INT UNSIGNED NOT NULL,
    `type` ENUM('group', 'teacher', 'place', 'subject') NOT NULL,
    `name` VARCHAR(30) NOT NULL,
    FULLTEXT (`name`)
);

CREATE TABLE `ej_groups` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(12) NOT NULL
);

CREATE TABLE `users` (
    `chat_id` VARCHAR(20) NOT NULL UNIQUE PRIMARY KEY,
    `rasp_entity` INT UNSIGNED,
    `sub_entity` INT UNSIGNED,
    `status` ENUM('user', 'group', 'admin') NOT NULL DEFAULT 'user',
    `ej_sub` BOOLEAN NOT NULL DEFAULT FALSE,
    `surname` VARCHAR(50),
    `ej_group` INT UNSIGNED,
    `birth` CHAR(10),
    `show_timestamps` BOOLEAN NOT NULL DEFAULT FALSE,
    `show_extended_info` BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (`rasp_entity`) REFERENCES `rasp_entities` (`id`),
    FOREIGN KEY (`sub_entity`) REFERENCES `rasp_entities` (`id`),
    FOREIGN KEY (`ej_group`) REFERENCES `ej_groups` (`id`)
);

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

CREATE TABLE ej_average_data (
    `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `chat_id` VARCHAR(20) NOT NULL,
    `name` VARCHAR(20) NOT NULL,
    `mark` VARCHAR(3) NOT NULL,
    FOREIGN KEY (`chat_id`) REFERENCES `users` (`chat_id`)
);
