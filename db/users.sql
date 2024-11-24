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
