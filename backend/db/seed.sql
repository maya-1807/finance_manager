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
    (11, 'Other',          NULL, NULL, '#607D8B'),
    (12, 'Restaurants',    NULL, NULL, '#FF6F00'),
    (13, 'Finance',        NULL, NULL, '#795548');

-- Common Israeli merchant classification rules
INSERT OR IGNORE INTO classification_rules (category_id, keyword, match_type) VALUES
    -- Food / Groceries (2)
    (2, 'שופרסל',       'contains'),
    (2, 'רמי לוי',      'contains'),
    (2, 'מגה',          'contains'),
    (2, 'ויקטורי',      'contains'),
    (2, 'יוחננוף',      'contains'),
    (2, 'אושר עד',      'contains'),
    (2, 'חצי חינם',     'contains'),
    (2, 'AM:PM',        'contains'),
    (2, 'מינימרקט',     'contains'),
    (2, 'סופר פאפא',    'contains'),
    (2, 'לחם משנה',     'contains'),
    -- Transport (3)
    (3, 'רב קו',        'contains'),
    (3, 'דלק',          'contains'),
    (3, 'סונול',        'contains'),
    (3, 'פז',           'starts_with'),
    (3, 'דור אלון',     'contains'),
    (3, 'דור עד',       'contains'),
    (3, 'כביש 6',       'contains'),
    (3, 'מנהרות הכרמל', 'contains'),
    (3, 'פנגו',         'contains'),
    (3, 'שלמה תחבורה',  'contains'),
    (3, 'ספרינט מוטורוס', 'contains'),
    (3, 'איתוראן',      'contains'),
    -- Entertainment (4)
    (4, 'סינמה',        'contains'),
    (4, 'יס פלאנט',     'contains'),
    (4, 'טן פארק',      'contains'),
    -- Health (5)
    (5, 'סופר פארם',    'contains'),
    (5, 'בי פארם',      'contains'),
    (5, 'בית מרקחת',    'contains'),
    (5, 'קרן מכבי',     'contains'),
    (5, 'IHERB',        'contains'),
    (5, 'גרין פארם',    'contains'),
    (5, 'דראגסטור',     'contains'),
    -- Clothing (6)
    (6, 'אורבניקה',     'contains'),
    (6, 'נולה סוקס',    'contains'),
    (6, 'ספרינג',       'contains'),
    -- Household (7)
    (7, 'ALIEXPRESS',   'contains'),
    (7, 'ETSY',         'contains'),
    (7, 'דוגי זול',     'contains'),
    -- Subscriptions (8)
    (8, 'נטפליקס',      'contains'),
    (8, 'NETFLIX',      'contains'),
    (8, 'SPOTIFY',      'contains'),
    (8, 'APPLE.COM',    'contains'),
    (8, 'CLAUDE.AI',    'contains'),
    (8, 'CURSOR.COM',   'contains'),
    (8, 'פרטנר',        'contains'),
    -- Education (9)
    (9, 'אגודת הסטודנטים', 'contains'),
    -- Restaurants (12)
    (12, 'WOLT',        'contains'),
    (12, 'YANGO DELI',  'contains'),
    (12, 'גפניקה',      'contains'),
    (12, 'מטילדה',      'contains'),
    (12, 'פאפיאנו',     'contains'),
    (12, 'סזאנקה',      'contains'),
    (12, 'קפה גרג',     'contains'),
    (12, 'תילנדית בשוק', 'contains'),
    (12, 'תמנון',       'contains'),
    (12, 'לגו - צפון',  'contains'),
    (12, 'סברס',        'contains'),
    -- Finance (13)
    (13, 'בנק הפועלים', 'contains'),
    (13, 'בנק לאומי',   'contains'),
    (13, 'החזר עמלה',   'contains'),
    (13, 'מאסטרקרד',    'contains'),
    (13, 'הפק` מזומן',  'contains'),
    (13, 'העברה ב BIT',  'contains'),
    (13, 'העברת משכורת', 'contains'),
    (13, 'BIT',         'exact'),
    (13, 'עמל.',        'starts_with'),
    -- Other (11)
    (11, 'ארגון רבני צהר', 'contains'),
    (11, 'איססלון',     'contains');

-- Schema version (matches latest migration applied in schema.sql)
INSERT OR IGNORE INTO schema_version (version) VALUES (1);
INSERT OR IGNORE INTO schema_version (version) VALUES (2);
