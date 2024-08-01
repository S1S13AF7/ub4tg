-- phpMyAdmin SQL Dump
--
-- Хост: localhost

--
-- БД: `db`
--

-- --------------------------------------------------------

--
-- Структура таблиці `tg_bot_users`
--

CREATE TABLE IF NOT EXISTS `tg_bot_users` (
  `user_id` bigint(20) unsigned NOT NULL DEFAULT '0',
  `reg_int` int(11) unsigned NOT NULL DEFAULT '0',
  `f_name` text NOT NULL,
  `mcoins` bigint(20) unsigned NOT NULL DEFAULT '1024',
  `rnd_kd` int(11) unsigned NOT NULL DEFAULT '0',
  `lng_code` varchar(8) NOT NULL DEFAULT '',
  PRIMARY KEY (`user_id`)
);

--

