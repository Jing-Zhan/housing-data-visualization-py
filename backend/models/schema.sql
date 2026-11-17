-- 城市居住数据可视化平台建表脚本
-- 结构沿用原医疗系统：13 个业务字段作为通用槽位，切换领域不需要改表

CREATE DATABASE IF NOT EXISTS housinginfo DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE housinginfo;

DROP TABLE IF EXISTS `cases`;
CREATE TABLE `cases` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `type` varchar(255) DEFAULT NULL COMMENT '户型',
  `gender` varchar(255) DEFAULT NULL COMMENT '装修',
  `age` varchar(255) DEFAULT NULL COMMENT '房龄',
  `time` varchar(255) DEFAULT NULL COMMENT '挂牌日期',
  `content` varchar(255) DEFAULT NULL COMMENT '标题与描述',
  `docName` varchar(255) DEFAULT NULL COMMENT '经纪人',
  `docHospital` varchar(255) DEFAULT NULL COMMENT '小区',
  `department` varchar(255) DEFAULT NULL COMMENT '区域',
  `detailUrl` varchar(2555) DEFAULT NULL COMMENT '详情链接',
  `height` varchar(255) DEFAULT NULL COMMENT '建筑面积',
  `weight` varchar(255) DEFAULT NULL COMMENT '挂牌总价',
  `illDuration` varchar(255) DEFAULT NULL COMMENT '楼层',
  `allergy` varchar(255) DEFAULT NULL COMMENT '朝向与权属',
  PRIMARY KEY (`id`),
  KEY `idx_type` (`type`),
  KEY `idx_department` (`department`),
  KEY `idx_time` (`time`),
  UNIQUE KEY `uk_detail` (`detailUrl`(191))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TABLE IF EXISTS `data_sources`;
CREATE TABLE `data_sources` (
  `id` int NOT NULL AUTO_INCREMENT,
  `code` varchar(64) NOT NULL COMMENT '数据源编码',
  `name` varchar(255) NOT NULL COMMENT '数据源名称',
  `disease` varchar(255) NOT NULL COMMENT '负责的类别（复用原字段名）',
  `type` varchar(50) NOT NULL DEFAULT 'crawler',
  `description` varchar(512) DEFAULT NULL,
  `enabled` tinyint(1) NOT NULL DEFAULT 1,
  `status` varchar(50) NOT NULL DEFAULT 'idle',
  `last_run_at` datetime DEFAULT NULL,
  `last_success_at` datetime DEFAULT NULL,
  `last_delta` int DEFAULT 0,
  `total_records` int DEFAULT 0,
  `last_message` varchar(1024) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TABLE IF EXISTS `data_versions`;
CREATE TABLE `data_versions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `version_code` varchar(64) NOT NULL,
  `operator` varchar(255) DEFAULT 'system',
  `action` varchar(64) NOT NULL,
  `description` varchar(1024) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `total_records` int DEFAULT 0,
  `delta_records` int DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TABLE IF EXISTS `cases_snapshot`;
CREATE TABLE `cases_snapshot` (
  `id` int NOT NULL AUTO_INCREMENT,
  `version_id` int NOT NULL,
  `case_id` int DEFAULT NULL,
  `type` varchar(255) DEFAULT NULL,
  `gender` varchar(255) DEFAULT NULL,
  `age` varchar(255) DEFAULT NULL,
  `time` varchar(255) DEFAULT NULL,
  `content` varchar(255) DEFAULT NULL,
  `docName` varchar(255) DEFAULT NULL,
  `docHospital` varchar(255) DEFAULT NULL,
  `department` varchar(255) DEFAULT NULL,
  `detailUrl` varchar(2555) DEFAULT NULL,
  `height` varchar(255) DEFAULT NULL,
  `weight` varchar(255) DEFAULT NULL,
  `illDuration` varchar(255) DEFAULT NULL,
  `allergy` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_version_id` (`version_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TABLE IF EXISTS `report_templates`;
CREATE TABLE `report_templates` (
  `id` varchar(64) NOT NULL,
  `name` varchar(255) NOT NULL,
  `type` varchar(50) NOT NULL,
  `scene` varchar(255) DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'draft',
  `version` varchar(20) NOT NULL DEFAULT '1.0',
  `blocks_json` json NOT NULL,
  `versions_json` json DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
