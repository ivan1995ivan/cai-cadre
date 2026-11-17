-- CAI ERP: administratorul „admin” creat direct în SQL Server (SSMS), când instalarea s-a întrerupt înainte de cont.
-- Parola temporară: Admin-2026. La prima intrare programul cere schimbarea ei.
-- Înainte de rulare: USE [baza voastră] (de ex. FLIX). Se poate rula de mai multe ori: contul existent primește
-- parola temporară din nou.
-- Altă parolă temporară: hash-ul se face cu manage.py shell -c "from django.contrib.auth.hashers import make_password; print(make_password('...'))".

DECLARE @pwd nvarchar(128) = N'pbkdf2_sha256$1200000$u5gRoFCkaXLcjQnyBgkiin$4SNL/tDCWW2fJek8GqrZKwaJGbm74qXMreiJGw+oFkc=';

IF NOT EXISTS (SELECT 1 FROM dbo.users_user WHERE username = N'admin')
    INSERT INTO dbo.users_user (password, last_login, is_superuser, username, first_name, last_name, email, is_staff,
                                is_active, date_joined, middle_name, phone, position, language, theme, density,
                                telegram_chat_id, margin_visibility, must_change_password, last_seen_version, tours_done,
                                favorites, is_manager)
    VALUES (@pwd, NULL, 1, N'admin', N'Administrator', N'', N'', 1, 1, SYSUTCDATETIME(), N'', N'', N'', N'ro', N'',
            N'normal', N'', N'inherit', 1, N'', N'[]', N'[]', 0);
ELSE
    UPDATE dbo.users_user
    SET password = @pwd, is_superuser = 1, is_staff = 1, is_active = 1, must_change_password = 1
    WHERE username = N'admin';

-- rolul „Administrator” (îl creează serverul la pornire)
INSERT INTO dbo.users_user_roles (user_id, role_id)
SELECT u.id, r.id
FROM dbo.users_user u CROSS JOIN dbo.users_role r
WHERE u.username = N'admin' AND r.code = N'admin'
  AND NOT EXISTS (SELECT 1 FROM dbo.users_user_roles x WHERE x.user_id = u.id AND x.role_id = r.id);

SELECT u.id, u.username, u.is_superuser, u.is_active, r.code AS rol
FROM dbo.users_user u
LEFT JOIN dbo.users_user_roles ur ON ur.user_id = u.id
LEFT JOIN dbo.users_role r ON r.id = ur.role_id
WHERE u.username = N'admin';
