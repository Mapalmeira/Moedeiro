CREATE TABLE user_preferences_v3 (
    user_uuid BLOB PRIMARY KEY,
    language TEXT NOT NULL,
    theme TEXT NOT NULL CHECK (theme IN ('LIGHT', 'DARK')),

    FOREIGN KEY (user_uuid) REFERENCES user_account(uuid) ON DELETE CASCADE
) STRICT;

INSERT INTO user_preferences_v3(user_uuid, language, theme)
SELECT user_uuid, language, theme
FROM user_preferences;

DROP TABLE user_preferences;
ALTER TABLE user_preferences_v3 RENAME TO user_preferences;
