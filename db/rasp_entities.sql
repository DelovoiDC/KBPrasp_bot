CREATE TABLE rasp_entities (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `entity_id` INT UNSIGNED NOT NULL,
    `type` ENUM('group', 'teacher', 'place', 'subject') NOT NULL,
    `name` VARCHAR(30) NOT NULL,
    FULLTEXT (`name`)
);
