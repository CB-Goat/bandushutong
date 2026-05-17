-- 将手机号 18674827052 的用户修改为系统管理员
UPDATE users SET role = 'admin' WHERE phone = '18674827052';

-- 验证修改结果
SELECT id, phone, role, created_at FROM users WHERE phone = '18674827052';
