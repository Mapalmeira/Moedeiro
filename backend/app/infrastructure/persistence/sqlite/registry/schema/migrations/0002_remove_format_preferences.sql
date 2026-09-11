CREATE TABLE user_preferences_v2 (
    user_uuid BLOB PRIMARY KEY,
    language TEXT NOT NULL,
    theme TEXT NOT NULL CHECK (theme IN ('LIGHT', 'DARK')),
    timezone TEXT NOT NULL CHECK (length(timezone) BETWEEN 1 AND 50),

    FOREIGN KEY (user_uuid) REFERENCES user_account(uuid) ON DELETE CASCADE
) STRICT;

INSERT INTO user_preferences_v2(user_uuid, language, theme, timezone)
SELECT user_uuid, language, theme, timezone
FROM user_preferences;

DROP TABLE user_preferences;
ALTER TABLE user_preferences_v2 RENAME TO user_preferences;
