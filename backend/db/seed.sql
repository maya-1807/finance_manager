-- Default categories
-- id=1 is "Uncategorized" used as fallback
INSERT OR IGNORE INTO categories (id, name, monthly_budget, icon, color) VALUES
    (1,  'Uncategorized',  NULL, NULL, '#9E9E9E'),
    (2,  'Food',           NULL, NULL, '#FF5722'),
    (3,  'Transport',      NULL, NULL, '#2196F3'),
    (4,  'Entertainment',  NULL, NULL, '#9C27B0'),
    (5,  'Health',         NULL, NULL, '#4CAF50'),
    (6,  'Clothing',       NULL, NULL, '#E91E63'),
    (7,  'Household',      NULL, NULL, '#FF9800'),
    (8,  'Subscriptions',  NULL, NULL, '#00BCD4'),
    (9,  'Education',      NULL, NULL, '#3F51B5'),
    (10, 'Gifts',          NULL, NULL, '#F44336'),
    (11, 'Other',          NULL, NULL, '#607D8B');

-- Common Israeli merchant classification rules
INSERT OR IGNORE INTO classification_rules (category_id, keyword, match_type) VALUES
    -- Food / Groceries
    (2, 'שופרסל',    'contains'),
    (2, 'רמי לוי',   'contains'),
    (2, 'מגה',       'contains'),
    (2, 'ויקטורי',   'contains'),
    (2, 'יוחננוף',   'contains'),
    (2, 'אושר עד',   'contains'),
    (2, 'חצי חינם',  'contains'),
    (2, 'AM:PM',     'contains'),
    -- Transport
    (3, 'רב קו',     'contains'),
    (3, 'דלק',       'contains'),
    (3, 'סונול',     'contains'),
    (3, 'פז',        'exact'),
    (3, 'דור אלון',  'contains'),
    -- Entertainment
    (4, 'סינמה',     'contains'),
    (4, 'יס פלאנט',  'contains'),
    -- Health
    (5, 'סופר פארם', 'contains'),
    (5, 'בי פארם',   'contains'),
    -- Subscriptions
    (8, 'נטפליקס',   'contains'),
    (8, 'NETFLIX',   'contains'),
    (8, 'SPOTIFY',   'contains'),
    (8, 'APPLE.COM', 'contains');

-- Initial schema version
INSERT OR IGNORE INTO schema_version (version) VALUES (1);
