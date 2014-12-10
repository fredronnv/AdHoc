-- phpMyAdmin SQL Dump
-- version 2.11.6
-- http://www.phpmyadmin.net
--
-- Host: adhoc.ita.chalmers.se
-- Generation Time: May 05, 2014 at 08:41 AM
-- Server version: 5.1.73
-- PHP Version: 5.1.4

SET SQL_MODE="NO_AUTO_VALUE_ON_ZERO";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;

--
-- Database: `AdHoc`
--
CREATE DATABASE `AdHoc` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE AdHoc;

-- --------------------------------------------------------

--
-- Table structure for table `account_privilege_map`
--

CREATE TABLE IF NOT EXISTS `account_privilege_map` (
  `account` varchar(8) COLLATE ascii_bin NOT NULL,
  `privilege` varchar(32) COLLATE ascii_bin NOT NULL,
  `changed_by` varchar(8) COLLATE ascii_bin NOT NULL,
  `mtime` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00' ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `account_2` (`account`,`privilege`),
  KEY `account` (`account`),
  KEY `privilege` (`privilege`)
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin COMMENT='Maps accounts to privileges';

INSERT INTO `account_privilege_map` (`account`, `privilege`) VALUES
('srvadhoc', 'read_all_privileges'),
('srvadhoc', 'grant_all_privileges');

-- --------------------------------------------------------

--
-- Table structure for table `accounts`
--

CREATE TABLE IF NOT EXISTS `accounts` (
  `account` varchar(8) COLLATE ascii_bin NOT NULL COMMENT 'PDB account',
  `fname` varchar(4000) CHARACTER SET utf8 COLLATE utf8_swedish_ci NOT NULL COMMENT 'First name of owner',
  `lname` varchar(4000) CHARACTER SET utf8 COLLATE utf8_swedish_ci NOT NULL COMMENT 'Last name of owner',
  PRIMARY KEY (`account`)
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin COMMENT='User accounts';

INSERT INTO `accounts` (`account`, `fname`, `lname`) VALUES
('srvadhoc', 'AdHoc','Server'),
('int_0002', 'PDB Integration','Agent');

-- --------------------------------------------------------

--
-- Table structure for table `bool_option`
--

CREATE TABLE IF NOT EXISTS `bool_option` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `option_base` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `option_base` (`option_base`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 AUTO_INCREMENT=2 ;


-- --------------------------------------------------------

--
-- Table structure for table `buildings`
--

CREATE TABLE IF NOT EXISTS `buildings` (
  `id` varchar(24) NOT NULL COMMENT 'Building id',
  `re` varchar(64) NOT NULL COMMENT 'Regex to match room codes for this building',
  `info` varchar(128) NOT NULL COMMENT 'building information',
  `changed_by` varchar(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'cid of last changer',
  `mtime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'time of last change',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Buildings table';


-- --------------------------------------------------------

--
-- Table structure for table `class_literal_options`
--

CREATE TABLE IF NOT EXISTS `class_literal_options` (
  `for` varchar(64) NOT NULL COMMENT 'Class on which to apply this option',
  `value` varchar(256) NOT NULL COMMENT 'Option value',
  `changed_by` varchar(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `id` int(11) NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`),
  KEY `for` (`for`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 COMMENT='Literal options for classes' AUTO_INCREMENT=4 ;

-- --------------------------------------------------------

--
-- Table structure for table `classes`
--

CREATE TABLE IF NOT EXISTS `classes` (
  `classname` varchar(64) NOT NULL COMMENT 'Name of class',
  `optionspace` varchar(16) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL COMMENT 'Option space, if any',
  `vendor_class_id` varchar(32) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL COMMENT 'Data for vendor class id stmt',
  `info` varchar(80) DEFAULT NULL COMMENT 'Class description',
  `changed_by` varchar(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `optionset` int(11) NOT NULL,
  PRIMARY KEY (`classname`),
  KEY `optionspace` (`optionspace`),
  KEY `optionset` (`optionset`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Table of classes';



-- --------------------------------------------------------

--
-- Table structure for table `dhcp_servers`
--

CREATE TABLE IF NOT EXISTS `dhcp_servers` (
  `name` varchar(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'DNS name of server',
  `info` varchar(80) NOT NULL COMMENT 'Server description',
  `id` char(1) NOT NULL COMMENT 'DHCP server id',
  `changed_by` varchar(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `latest_fetch` int(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='List of dhcp servers';



-- --------------------------------------------------------

--
-- Table structure for table `global_options`
--

CREATE TABLE IF NOT EXISTS `global_options` (
  `name` varchar(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `value` varchar(1024) NOT NULL,
  `changed_by` varchar(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `mtime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`),
  KEY `name` (`name`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 COMMENT='Table holding options global to the servers' AUTO_INCREMENT=1465 ;

-- --------------------------------------------------------

--
-- Table structure for table `group_groups_flat`
--

CREATE TABLE IF NOT EXISTS `group_groups_flat` (
  `groupname` varchar(64) NOT NULL,
  `descendant` varchar(64) NOT NULL,
  UNIQUE KEY `groupname_2` (`groupname`,`descendant`),
  KEY `groupname` (`groupname`,`descendant`),
  KEY `descendant` (`descendant`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Flattens out the group tree.';



-- --------------------------------------------------------

--
-- Table structure for table `group_literal_options`
--

CREATE TABLE IF NOT EXISTS `group_literal_options` (
  `for` varchar(64) NOT NULL COMMENT 'Group on which to apply this option',
  `value` varchar(256) NOT NULL COMMENT 'Option value',
  `changed_by` varchar(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `id` int(11) NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`),
  KEY `for` (`for`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 COMMENT='Literal options for groups';


-- --------------------------------------------------------

--
-- Table structure for table `groups`
--

CREATE TABLE IF NOT EXISTS `groups` (
  `groupname` varchar(64) NOT NULL COMMENT 'Group name',
  `optionspace` varchar(16) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL COMMENT 'Option space',
  `parent_group` varchar(64) NOT NULL COMMENT 'Parent group',
  `info` varchar(80) DEFAULT NULL COMMENT 'Information on the group',
  `changed_by` varchar(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `optionset` int(11) NOT NULL,
  `hostcount` int(11) NOT NULL DEFAULT '0' COMMENT 'Current number of active hosts, including subgroups',
  PRIMARY KEY (`groupname`),
  KEY `optionspace` (`optionspace`),
  KEY `parent_group` (`parent_group`),
  KEY `optionset` (`optionset`),
  KEY `hostcount` (`hostcount`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Table of host groups';

-- --------------------------------------------------------

--
-- Table structure for table `host_literal_options`
--

CREATE TABLE IF NOT EXISTS `host_literal_options` (
  `for` varchar(64) NOT NULL COMMENT 'Host on which to apply this option',
  `value` varchar(256) NOT NULL COMMENT 'Option value',
  `changed_by` varchar(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `id` int(11) NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`),
  KEY `for` (`for`),
  KEY `value` (`value`(255))
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Literal options for hosts' AUTO_INCREMENT=1 ;


-- --------------------------------------------------------

--
-- Table structure for table `hosts`
--

CREATE TABLE IF NOT EXISTS `hosts` (
  `id` varchar(64) NOT NULL COMMENT 'Host ID',
  `dns` varchar(255) CHARACTER SET ascii COLLATE ascii_bin DEFAULT 'localhost' COMMENT 'DNS name',
  `group` varchar(64) DEFAULT 'plain' COMMENT 'Group where the host belongs',
  `mac` varchar(17) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT '00:00:00:00:00:00' COMMENT 'Mac address',
  `room` varchar(10) DEFAULT NULL COMMENT 'Room code',
  `optionspace` varchar(16) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL COMMENT 'Option space to define',
  `changed_by` varchar(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `info` varchar(80) DEFAULT NULL COMMENT 'Host comment',
  `entry_status` varchar(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'Active',
  `optionset` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `dns` (`dns`),
  KEY `group` (`group`),
  KEY `mac` (`mac`),
  KEY `entry_status` (`entry_status`),
  KEY `room` (`room`),
  KEY `optionspace` (`optionspace`),
  KEY `optionset` (`optionset`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='List of hosts';


-- --------------------------------------------------------

--
-- Table structure for table `int_option`
--

CREATE TABLE IF NOT EXISTS `int_option` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `option_base` int(11) NOT NULL,
  `minval` int(11) DEFAULT NULL,
  `maxval` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `option_base` (`option_base`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;


-- --------------------------------------------------------

--
-- Table structure for table `intarray_option`
--

CREATE TABLE IF NOT EXISTS `intarray_option` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `option_base` int(11) NOT NULL,
  `minval` int(11) DEFAULT NULL,
  `maxval` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `option_base` (`option_base`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;


-- --------------------------------------------------------

--
-- Table structure for table `ipaddr_option`
--

CREATE TABLE IF NOT EXISTS `ipaddr_option` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `option_base` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `option_base` (`option_base`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;


-- --------------------------------------------------------

--
-- Table structure for table `ipaddrarray_option`
--

CREATE TABLE IF NOT EXISTS `ipaddrarray_option` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `option_base` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `option_base` (`option_base`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `networks`
--

CREATE TABLE IF NOT EXISTS `networks` (
  `id` varchar(64) NOT NULL COMMENT 'Name of network',
  `authoritative` int(1) NOT NULL DEFAULT '1' COMMENT 'Whether the network is authoritative or nor',
  `info` varchar(80) DEFAULT NULL COMMENT 'Network description',
  `changed_by` varchar(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `optionset` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `optionspace` (`authoritative`),
  KEY `optionset` (`optionset`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Table of shared networks';

-- --------------------------------------------------------

--
-- Table structure for table `option_base`
--

CREATE TABLE IF NOT EXISTS `option_base` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(64) DEFAULT NULL,
  `info` varchar(1024) DEFAULT NULL,
  `guard` varchar(64) DEFAULT NULL,
  `from_api` smallint(6) NOT NULL DEFAULT '0',
  `to_api` smallint(6) NOT NULL DEFAULT '10000',
  `code` int(3) DEFAULT NULL COMMENT 'Numeric code in DHCP protocol',
  `qualifier` enum('array','parameter','parameter-array') CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL COMMENT 'Adjustments to the option. Array and/or parameter. A parameter is a standard DHSP option defined here.',
  `type` enum('ip-address','text','unsigned integer 8','unsigned integer 16','unsigned integer 32','integer 8','integer 16','integer 32','string','boolean') CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'text',
  `optionspace` varchar(16) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL COMMENT 'Optionspace that has to be defined to use this option, if any.',
  `encapsulate` varchar(16) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL COMMENT 'The option space that is to be encapsulated by this option, if any.',
  `struct` varchar(1024) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL COMMENT 'The option is a record defined by the structure definition given here.',
  `changed_by` varchar(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Time of last change',
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `optionspace` (`optionspace`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 AUTO_INCREMENT=110 ;

--
-- Table structure for table `optionset`
--

CREATE TABLE IF NOT EXISTS `optionset` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;


-- --------------------------------------------------------

--
-- Table structure for table `optionset_boolval`
--

CREATE TABLE IF NOT EXISTS `optionset_boolval` (
  `bool_option` int(11) NOT NULL,
  `optionset` int(11) NOT NULL,
  `value` char(1) NOT NULL,
  UNIQUE KEY `bool_option` (`bool_option`,`optionset`),
  KEY `optionset` (`optionset`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;



-- --------------------------------------------------------

--
-- Table structure for table `optionset_intarrayval`
--

CREATE TABLE IF NOT EXISTS `optionset_intarrayval` (
  `intarray_option` int(11) NOT NULL,
  `optionset` int(11) NOT NULL,
  `value` varchar(4000) NOT NULL COMMENT 'Integer array coded as a pickled string',
  UNIQUE KEY `int_option` (`intarray_option`,`optionset`),
  KEY `optionset` (`optionset`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `optionset_intval`
--

CREATE TABLE IF NOT EXISTS `optionset_intval` (
  `int_option` int(11) NOT NULL,
  `optionset` int(11) NOT NULL,
  `value` int(11) NOT NULL,
  UNIQUE KEY `int_option` (`int_option`,`optionset`),
  KEY `optionset` (`optionset`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `optionset_ipaddrarrayval`
--

CREATE TABLE IF NOT EXISTS `optionset_ipaddrarrayval` (
  `ipaddrarray_option` int(11) NOT NULL,
  `optionset` int(11) NOT NULL,
  `value` varchar(4000) NOT NULL COMMENT 'IP arrat pickle coded',
  UNIQUE KEY `bool_option` (`ipaddrarray_option`,`optionset`),
  KEY `optionset` (`optionset`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `optionset_ipaddrval`
--

CREATE TABLE IF NOT EXISTS `optionset_ipaddrval` (
  `ipaddr_option` int(11) NOT NULL,
  `optionset` int(11) NOT NULL,
  `value` varchar(64) NOT NULL,
  UNIQUE KEY `bool_option` (`ipaddr_option`,`optionset`),
  KEY `optionset` (`optionset`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `optionset_strval`
--

CREATE TABLE IF NOT EXISTS `optionset_strval` (
  `str_option` int(11) NOT NULL,
  `optionset` int(11) NOT NULL,
  `value` varchar(1024) NOT NULL,
  UNIQUE KEY `str_option` (`str_option`,`optionset`),
  KEY `optionset` (`optionset`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `optionspaces`
--

CREATE TABLE IF NOT EXISTS `optionspaces` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT 'Id of option space',
  `value` varchar(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'Option space name',
  `type` enum('vendor','site') CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'Vendor or site space',
  `info` varchar(80) DEFAULT NULL COMMENT 'Class description',
  `changed_by` varchar(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Time of last change',
  PRIMARY KEY (`id`),
  UNIQUE KEY `value` (`value`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 COMMENT='Definitions of option spaces';

-- --------------------------------------------------------

--
-- Table structure for table `pool_class_map`
--

CREATE TABLE IF NOT EXISTS `pool_class_map` (
  `poolname` varchar(64) NOT NULL COMMENT 'Pool where the host may live',
  `classname` varchar(64) NOT NULL COMMENT 'Class name',
  `changed_by` varchar(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Time of last change',
  UNIQUE KEY `poolname_2` (`poolname`,`classname`),
  KEY `classname` (`classname`),
  KEY `poolname` (`poolname`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Defines which classes may live in which pools';


-- --------------------------------------------------------

--
-- Table structure for table `pool_group_map`
--

CREATE TABLE IF NOT EXISTS `pool_group_map` (
  `poolname` varchar(64) NOT NULL COMMENT 'Pool where the group may live',
  `groupname` varchar(64) NOT NULL COMMENT 'Group name',
  `changed_by` varchar(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Time of last change',
  UNIQUE KEY `poolname_2` (`poolname`,`groupname`),
  KEY `groupname` (`groupname`),
  KEY `poolname` (`poolname`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Defines which groups that may live in which pools';

-- --------------------------------------------------------

--
-- Table structure for table `pool_host_map`
--

CREATE TABLE IF NOT EXISTS `pool_host_map` (
  `poolname` varchar(64) NOT NULL COMMENT 'Pool where the host may live',
  `hostname` varchar(64) NOT NULL COMMENT 'Class name',
  `changed_by` varchar(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Time of last change',
  UNIQUE KEY `poolname_2` (`poolname`,`hostname`),
  KEY `classname` (`hostname`),
  KEY `poolname` (`poolname`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Defines which classes may live in which pools';

-- --------------------------------------------------------

--
-- Table structure for table `pool_literal_options`
--

CREATE TABLE IF NOT EXISTS `pool_literal_options` (
  `for` varchar(64) NOT NULL COMMENT 'Pool on which to apply this option',
  `value` varchar(256) NOT NULL COMMENT 'Option value',
  `changed_by` varchar(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `id` int(11) NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`),
  KEY `for` (`for`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Literal options for pools';

-- --------------------------------------------------------

--
-- Table structure for table `pool_ranges`
--

CREATE TABLE IF NOT EXISTS `pool_ranges` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `pool` varchar(64) NOT NULL COMMENT 'Name of pool this range belongs to',
  `start_ip` varchar(15) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'First IP of range',
  `end_ip` varchar(15) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'Last IP of range',
  `served_by` char(1) NOT NULL DEFAULT 'A' COMMENT 'DHCP server serving this range',
  `changed_by` varchar(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Time of last change',
  PRIMARY KEY (`id`),
  UNIQUE KEY `start_ip` (`start_ip`),
  UNIQUE KEY `end_ip` (`end_ip`),
  UNIQUE KEY `start_ip_2` (`start_ip`,`end_ip`),
  KEY `pool` (`pool`),
  KEY `served_by` (`served_by`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 COMMENT='Table IP ranges for pools';

-- --------------------------------------------------------

--
-- Table structure for table `pools`
--

CREATE TABLE IF NOT EXISTS `pools` (
  `poolname` varchar(64) NOT NULL COMMENT 'Name of pool',
  `optionspace` varchar(16) CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL COMMENT 'Option space, if any',
  `max_lease_time` int(32) NOT NULL DEFAULT '600',
  `network` varchar(64) DEFAULT NULL COMMENT 'Network the pool belongs to',
  `info` varchar(80) DEFAULT NULL COMMENT 'Pool description',
  `changed_by` varchar(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `optionset` int(11) NOT NULL,
  PRIMARY KEY (`poolname`),
  KEY `optionspace` (`optionspace`),
  KEY `network` (`network`),
  KEY `optionset` (`optionset`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Table of pools';

-- --------------------------------------------------------

--
-- Table structure for table `privileges`
--

CREATE TABLE IF NOT EXISTS `privileges` (
  `privilege` varchar(32) COLLATE ascii_bin NOT NULL COMMENT 'Privilege id',
  `info` varchar(64) CHARACTER SET utf8 COLLATE utf8_swedish_ci NOT NULL COMMENT 'Description',
  PRIMARY KEY (`privilege`)
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin COMMENT='Privileges list';

--
-- Dumping data for table `privileges`
--

INSERT INTO `privileges` (`privilege`, `info`) VALUES
('admin_all_pools', 'Privilege group for the AdHoc DHCP management system'),
('grant_all_privileges', 'Privilege group for the AdHoc DHCP management system'),
('read_all_accounts', ''),
('read_all_buildings', 'Privilege group for the AdHoc DHCP management system'),
('read_all_groups', 'Privilege group for the AdHoc DHCP management system'),
('read_all_hosts', 'Privilege group for the AdHoc DHCP management system'),
('read_all_privileges', ''),
('rename_all_objects', 'Privilege group for the AdHoc DHCP management system'),
('write_all_accounts', ''),
('write_all_buildings', 'Privilege group for the AdHoc DHCP management system'),
('write_all_global_options', 'Privilege group for the AdHoc DHCP management system'),
('write_all_groups', 'Privilege group for the AdHoc DHCP management system'),
('write_all_host_classes', 'Privilege group for the AdHoc DHCP management system'),
('write_all_hosts', 'Privilege group for the AdHoc DHCP management system'),
('write_all_networks', 'Privilege group for the AdHoc DHCP management system'),
('write_all_option_defs', 'Privilege group for the AdHoc DHCP management system'),
('write_all_optionsets', 'Privilege group for the AdHoc DHCP management system'),
('write_all_optionspaces', 'Privilege group for the AdHoc DHCP management system'),
('write_all_pool_ranges', 'Privilege group for the AdHoc DHCP management system'),
('write_all_pools', 'Privilege group for the AdHoc DHCP management system'),
('write_all_privileges', ''),
('write_all_rooms', 'Privilege group for the AdHoc DHCP management system'),
('write_all_subnetworks', 'Privilege group for the AdHoc DHCP management system'),
('write_literal_options', 'Privilege group for the AdHoc DHCP management system');

-- --------------------------------------------------------

--
-- Table structure for table `rooms`
--

CREATE TABLE IF NOT EXISTS `rooms` (
  `id` varchar(10) NOT NULL COMMENT 'Room ID',
  `info` varchar(80) DEFAULT NULL COMMENT 'Room description',
  `printers` varchar(1024) DEFAULT NULL COMMENT 'Printer list, if any',
  `changed_by` varchar(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'cid of last changer',
  `mtime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'time of last change',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='List of defined rooms';

-- --------------------------------------------------------

--
-- Table structure for table `rpcc_api_version`
--

CREATE TABLE IF NOT EXISTS `rpcc_api_version` (
  `version` int(11) NOT NULL,
  `state` char(1) NOT NULL,
  `comment` varchar(2048) DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Dumping data for table `rpcc_api_version`
--

INSERT INTO `rpcc_api_version` (`version`, `state`, `comment`) VALUES
(0, 'p', NULL);

-- --------------------------------------------------------

--
-- Table structure for table `rpcc_event`
--

CREATE TABLE IF NOT EXISTS `rpcc_event` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `typ` int(11) NOT NULL,
  `created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `parent` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `parent` (`parent`),
  KEY `created` (`created`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;


-- --------------------------------------------------------

--
-- Table structure for table `rpcc_event_int`
--

CREATE TABLE IF NOT EXISTS `rpcc_event_int` (
  `event` int(11) NOT NULL,
  `attr` int(11) NOT NULL,
  `value` int(11) DEFAULT NULL,
  UNIQUE KEY `rpcc_idx_evint` (`event`,`attr`),
  KEY `attr` (`attr`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;


-- --------------------------------------------------------

--
-- Table structure for table `rpcc_event_int_attr`
--

CREATE TABLE IF NOT EXISTS `rpcc_event_int_attr` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(32) CHARACTER SET latin1 NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `rpcc_idx_evintattr_name` (`name`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;

--
-- Dumping data for table `rpcc_event_int_attr`
--

INSERT INTO `rpcc_event_int_attr` (`id`, `name`) VALUES
(5, 'code'),
(1, 'elapsed'),
(6, 'maxval'),
(8, 'max_lease_time'),
(7, 'minval'),
(3, 'newint'),
(2, 'oldint'),
(4, 'optionset'),
(9, 'literal_option_id');

-- --------------------------------------------------------

--
-- Table structure for table `rpcc_event_str`
--

CREATE TABLE IF NOT EXISTS `rpcc_event_str` (
  `event` int(11) NOT NULL,
  `attr` int(11) NOT NULL,
  `value` varchar(2000) CHARACTER SET latin1 DEFAULT NULL,
  UNIQUE KEY `rpcc_idx_evstr` (`event`,`attr`),
  KEY `attr` (`attr`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;


-- --------------------------------------------------------

--
-- Table structure for table `rpcc_event_str_attr`
--

CREATE TABLE IF NOT EXISTS `rpcc_event_str_attr` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(32) CHARACTER SET latin1 NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `rpcc_idx_evstrattr_name` (`name`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;

--
-- Dumping data for table `rpcc_event_str_attr`
--

INSERT INTO `rpcc_event_str_attr` (`id`, `name`) VALUES
(27, 'authuser'),
(21, 'building'),
(12, 'host_class'),
(22, 'dhcp_server'),
(31, 'dns'),
(32, 'end_ip'),
(5, 'errid'),
(6, 'errline'),
(3, 'error'),
(4, 'errval'),
(1, 'function'),
(19, 'global_option'),
(11, 'group'),
(10, 'host'),
(23, 'info'),
(17, 'literal_option_value'),
(25, 'mtime'),
(13, 'network'),
(8, 'newstr'),
(9, 'oldstr'),
(26, 'option'),
(18, 'optionspace'),
(34, 'option_value'),
(2, 'params'),
(30, 'parent_object'),
(15, 'pool'),
(16, 'pool_range'),
(29, 'qualifier'),
(24, 're'),
(20, 'room'),
(7, 'stack'),
(33, 'start_ip'),
(14, 'subnetwork'),
(28, 'type'),
(36, 'printers'),
(37, 'mac'),
(38, 'entry_status'),
(40, 'authoritative'),
(41, 'served_by'),
(42, 'vendor_class_id'),
(43, 'id'),
(44, 'value');

-- --------------------------------------------------------

--
-- Table structure for table `rpcc_event_type`
--

CREATE TABLE IF NOT EXISTS `rpcc_event_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(32) CHARACTER SET latin1 NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `rpcc_idx_evtype` (`name`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;

--
-- Dumping data for table `rpcc_event_type`
--

INSERT INTO `rpcc_event_type` (`id`, `name`) VALUES
(2, 'call'),
(6, 'connect'),
(3, 'create'),
(5, 'destroy'),
(7, 'disconnect'),
(9, 'grant_access'),
(1, 'marker'),
(8, 'rename'),
(10, 'revoke_access'),
(4, 'update');

-- --------------------------------------------------------

--
-- Table structure for table `rpcc_mutex`
--

CREATE TABLE IF NOT EXISTS `rpcc_mutex` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT 'Mutex id',
  `name` varchar(64) COLLATE ascii_bin NOT NULL COMMENT 'Mutex name',
  `holder_session` varchar(40) COLLATE ascii_bin NOT NULL COMMENT 'Session of holder',
  `holder_public` varchar(128) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL COMMENT 'Public name of holder',
  `last_change` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `forced` char(1) COLLATE ascii_bin NOT NULL COMMENT 'Whether stolen or not. (Y/N)',
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin COMMENT='Rpcc Mutex list' AUTO_INCREMENT=1 ;


-- --------------------------------------------------------

--
-- Table structure for table `rpcc_mutex_var`
--

CREATE TABLE IF NOT EXISTS `rpcc_mutex_var` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `mutex_id` int(11) NOT NULL,
  `name` varchar(64) COLLATE ascii_bin NOT NULL,
  `collection` char(1) COLLATE ascii_bin NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `mutex_id_2` (`mutex_id`,`name`),
  KEY `mutex_id` (`mutex_id`)
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin COMMENT='Table holding mutex variables' AUTO_INCREMENT=1 ;


-- --------------------------------------------------------

--
-- Table structure for table `rpcc_mutex_var_val`
--

CREATE TABLE IF NOT EXISTS `rpcc_mutex_var_val` (
  `var` int(11) NOT NULL COMMENT 'ref to variable',
  `value` varchar(256) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL COMMENT 'Value of variable',
  KEY `var` (`var`)
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin COMMENT='Rpcc mutex variable values';

-- --------------------------------------------------------

--
-- Table structure for table `rpcc_result`
--

CREATE TABLE IF NOT EXISTS `rpcc_result` (
  `resid` int(11) NOT NULL COMMENT 'Result identifier',
  `manager` varchar(32) COLLATE ascii_bin NOT NULL COMMENT 'Reference to the code that is supposed to handle the result.',
  `expires` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Time when result can be deleted.',
  PRIMARY KEY (`resid`)
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin COMMENT='Table for search result sets';


-- --------------------------------------------------------

--
-- Table structure for table `rpcc_result_int`
--

CREATE TABLE IF NOT EXISTS `rpcc_result_int` (
  `resid` int(11) NOT NULL COMMENT 'Reference to resultset',
  `value` int(11) DEFAULT NULL COMMENT 'An integer value in the result set',
  KEY `resid` (`resid`),
  KEY `value` (`value`)
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin COMMENT='Results that are integers, per result ID';


-- --------------------------------------------------------

--
-- Table structure for table `rpcc_result_string`
--

CREATE TABLE IF NOT EXISTS `rpcc_result_string` (
  `resid` int(11) NOT NULL COMMENT 'Reference to resultset',
  `value` varchar(128) COLLATE utf8_bin DEFAULT NULL COMMENT 'A string value in the result set',
  KEY `resid` (`resid`),
  KEY `value` (`value`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Results that are strings, per result ID';

-- --------------------------------------------------------

--
-- Table structure for table `rpcc_session`
--

CREATE TABLE IF NOT EXISTS `rpcc_session` (
  `id` varchar(40) COLLATE ascii_bin NOT NULL COMMENT 'Session key',
  `expires` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00' COMMENT 'Time whensession expires',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin COMMENT='RPCC session management';


-- --------------------------------------------------------

--
-- Table structure for table `rpcc_session_string`
--

CREATE TABLE IF NOT EXISTS `rpcc_session_string` (
  `session_id` varchar(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'Reference to session ID',
  `name` varchar(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'Name of variable',
  `value` varchar(30) COLLATE utf8_bin DEFAULT NULL COMMENT 'Value of variable',
  KEY `session_id` (`session_id`),
  KEY `name` (`name`),
  KEY `value` (`value`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Table for storing data for a session';


-- --------------------------------------------------------

--
-- Table structure for table `str_option`
--

CREATE TABLE IF NOT EXISTS `str_option` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `option_base` int(11) NOT NULL,
  `regexp_constraint` varchar(128) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `option_base` (`option_base`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 AUTO_INCREMENT=70 ;


-- --------------------------------------------------------

--
-- Table structure for table `subnetworks`
--

CREATE TABLE IF NOT EXISTS `subnetworks` (
  `id` varchar(18) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT '129.16/16' COMMENT 'First IP of subnetwork',
  `network` varchar(64) DEFAULT NULL COMMENT 'Network the subnetwork belongs to',
  `info` varchar(80) DEFAULT NULL COMMENT 'Subnetwork description',
  `changed_by` varchar(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `optionset` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `network` (`network`),
  KEY `optionset` (`optionset`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Table of sub-networks';

--
-- Constraints for dumped tables
--

--
-- Constraints for table `account_privilege_map`
--
ALTER TABLE `account_privilege_map`
  ADD CONSTRAINT `account_privilege_map_ibfk_1` FOREIGN KEY (`account`) REFERENCES `accounts` (`account`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `account_privilege_map_ibfk_2` FOREIGN KEY (`privilege`) REFERENCES `privileges` (`privilege`);

--
-- Constraints for table `bool_option`
--
ALTER TABLE `bool_option`
  ADD CONSTRAINT `bool_option_ibfk_1` FOREIGN KEY (`option_base`) REFERENCES `option_base` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `class_literal_options`
--
ALTER TABLE `class_literal_options`
  ADD CONSTRAINT `class_literal_options_ibfk_1` FOREIGN KEY (`for`) REFERENCES `classes` (`classname`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `classes`
--
ALTER TABLE `classes`
  ADD CONSTRAINT `classes_ibfk_3` FOREIGN KEY (`optionspace`) REFERENCES `optionspaces` (`value`) ON UPDATE CASCADE,
  ADD CONSTRAINT `classes_ibfk_4` FOREIGN KEY (`optionset`) REFERENCES `optionset` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `group_groups_flat`
--
ALTER TABLE `group_groups_flat`
  ADD CONSTRAINT `group_groups_flat_ibfk_1` FOREIGN KEY (`groupname`) REFERENCES `groups` (`groupname`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `group_groups_flat_ibfk_2` FOREIGN KEY (`descendant`) REFERENCES `groups` (`groupname`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `group_literal_options`
--
ALTER TABLE `group_literal_options`
  ADD CONSTRAINT `group_literal_options_ibfk_1` FOREIGN KEY (`for`) REFERENCES `groups` (`groupname`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `groups`
--
ALTER TABLE `groups`
  ADD CONSTRAINT `groups_ibfk_10` FOREIGN KEY (`parent_group`) REFERENCES `groups` (`groupname`) ON UPDATE CASCADE,
  ADD CONSTRAINT `groups_ibfk_11` FOREIGN KEY (`optionset`) REFERENCES `optionset` (`id`) ON UPDATE CASCADE,
  ADD CONSTRAINT `groups_ibfk_9` FOREIGN KEY (`optionspace`) REFERENCES `optionspaces` (`value`) ON UPDATE CASCADE;

--
-- Constraints for table `host_literal_options`
--
ALTER TABLE `host_literal_options`
  ADD CONSTRAINT `host_literal_options_ibfk_1` FOREIGN KEY (`for`) REFERENCES `hosts` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `hosts`
--
ALTER TABLE `hosts`
  ADD CONSTRAINT `hosts_ibfk_15` FOREIGN KEY (`optionset`) REFERENCES `optionset` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `hosts_ibfk_20` FOREIGN KEY (`group`) REFERENCES `groups` (`groupname`) ON UPDATE CASCADE,
  ADD CONSTRAINT `hosts_ibfk_21` FOREIGN KEY (`room`) REFERENCES `rooms` (`id`) ON UPDATE CASCADE,
  ADD CONSTRAINT `hosts_ibfk_22` FOREIGN KEY (`optionspace`) REFERENCES `optionspaces` (`value`) ON UPDATE CASCADE;

--
-- Constraints for table `int_option`
--
ALTER TABLE `int_option`
  ADD CONSTRAINT `int_option_ibfk_1` FOREIGN KEY (`option_base`) REFERENCES `option_base` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `intarray_option`
--
ALTER TABLE `intarray_option`
  ADD CONSTRAINT `intarray_option_ibfk_1` FOREIGN KEY (`option_base`) REFERENCES `option_base` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `ipaddr_option`
--
ALTER TABLE `ipaddr_option`
  ADD CONSTRAINT `ipaddr_option_ibfk_1` FOREIGN KEY (`option_base`) REFERENCES `option_base` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `ipaddrarray_option`
--
ALTER TABLE `ipaddrarray_option`
  ADD CONSTRAINT `ipaddrarray_option_ibfk_1` FOREIGN KEY (`option_base`) REFERENCES `option_base` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `networks`
--
ALTER TABLE `networks`
  ADD CONSTRAINT `networks_ibfk_1` FOREIGN KEY (`optionset`) REFERENCES `optionset` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `option_base`
--
ALTER TABLE `option_base`
  ADD CONSTRAINT `option_base_ibfk_1` FOREIGN KEY (`optionspace`) REFERENCES `optionspaces` (`value`) ON UPDATE CASCADE;

--
-- Constraints for table `optionset_boolval`
--
ALTER TABLE `optionset_boolval`
  ADD CONSTRAINT `optionset_boolval_ibfk_3` FOREIGN KEY (`bool_option`) REFERENCES `bool_option` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `optionset_boolval_ibfk_4` FOREIGN KEY (`optionset`) REFERENCES `optionset` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `optionset_intarrayval`
--
ALTER TABLE `optionset_intarrayval`
  ADD CONSTRAINT `optionset_intarrayval_ibfk_2` FOREIGN KEY (`optionset`) REFERENCES `optionset` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `optionset_intval`
--
ALTER TABLE `optionset_intval`
  ADD CONSTRAINT `optionset_intval_ibfk_3` FOREIGN KEY (`int_option`) REFERENCES `int_option` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `optionset_intval_ibfk_4` FOREIGN KEY (`optionset`) REFERENCES `optionset` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `optionset_ipaddrarrayval`
--
ALTER TABLE `optionset_ipaddrarrayval`
  ADD CONSTRAINT `optionset_ipaddrarrayval_ibfk_1` FOREIGN KEY (`ipaddrarray_option`) REFERENCES `ipaddrarray_option` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `optionset_ipaddrarrayval_ibfk_2` FOREIGN KEY (`optionset`) REFERENCES `optionset` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `optionset_ipaddrval`
--
ALTER TABLE `optionset_ipaddrval`
  ADD CONSTRAINT `optionset_ipaddrval_ibfk_6` FOREIGN KEY (`ipaddr_option`) REFERENCES `ipaddr_option` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `optionset_ipaddrval_ibfk_7` FOREIGN KEY (`optionset`) REFERENCES `optionset` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `optionset_strval`
--
ALTER TABLE `optionset_strval`
  ADD CONSTRAINT `optionset_strval_ibfk_3` FOREIGN KEY (`str_option`) REFERENCES `str_option` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `optionset_strval_ibfk_4` FOREIGN KEY (`optionset`) REFERENCES `optionset` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `pool_class_map`
--
ALTER TABLE `pool_class_map`
  ADD CONSTRAINT `pool_class_map_ibfk_1` FOREIGN KEY (`poolname`) REFERENCES `pools` (`poolname`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `pool_class_map_ibfk_2` FOREIGN KEY (`classname`) REFERENCES `classes` (`classname`);

--
-- Constraints for table `pool_group_map`
--
ALTER TABLE `pool_group_map`
  ADD CONSTRAINT `pool_group_map_ibfk_3` FOREIGN KEY (`poolname`) REFERENCES `pools` (`poolname`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `pool_group_map_ibfk_4` FOREIGN KEY (`groupname`) REFERENCES `groups` (`groupname`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `pool_host_map`
--
ALTER TABLE `pool_host_map`
  ADD CONSTRAINT `pool_host_map_ibfk_1` FOREIGN KEY (`poolname`) REFERENCES `pools` (`poolname`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `pool_host_map_ibfk_2` FOREIGN KEY (`hostname`) REFERENCES `hosts` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `pool_literal_options`
--
ALTER TABLE `pool_literal_options`
  ADD CONSTRAINT `pool_literal_options_ibfk_1` FOREIGN KEY (`for`) REFERENCES `pools` (`poolname`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `pool_ranges`
--
ALTER TABLE `pool_ranges`
  ADD CONSTRAINT `pool_ranges_ibfk_1` FOREIGN KEY (`pool`) REFERENCES `pools` (`poolname`) ON UPDATE CASCADE,
  ADD CONSTRAINT `pool_ranges_ibfk_2` FOREIGN KEY (`served_by`) REFERENCES `dhcp_servers` (`id`) ON UPDATE CASCADE;

--
-- Constraints for table `pools`
--
ALTER TABLE `pools`
  ADD CONSTRAINT `pools_ibfk_3` FOREIGN KEY (`optionspace`) REFERENCES `optionspaces` (`value`) ON UPDATE CASCADE,
  ADD CONSTRAINT `pools_ibfk_4` FOREIGN KEY (`network`) REFERENCES `networks` (`id`) ON UPDATE CASCADE,
  ADD CONSTRAINT `pools_ibfk_5` FOREIGN KEY (`optionset`) REFERENCES `optionset` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `rpcc_event_int`
--
ALTER TABLE `rpcc_event_int`
  ADD CONSTRAINT `rpcc_event_int_ibfk_1` FOREIGN KEY (`event`) REFERENCES `rpcc_event` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `rpcc_event_int_ibfk_2` FOREIGN KEY (`attr`) REFERENCES `rpcc_event_int_attr` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `rpcc_event_str`
--
ALTER TABLE `rpcc_event_str`
  ADD CONSTRAINT `rpcc_event_str_ibfk_3` FOREIGN KEY (`event`) REFERENCES `rpcc_event` (`id`),
  ADD CONSTRAINT `rpcc_event_str_ibfk_4` FOREIGN KEY (`attr`) REFERENCES `rpcc_event_str_attr` (`id`);

--
-- Constraints for table `rpcc_mutex_var`
--
ALTER TABLE `rpcc_mutex_var`
  ADD CONSTRAINT `rpcc_mutex_var_ibfk_1` FOREIGN KEY (`mutex_id`) REFERENCES `rpcc_mutex` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `rpcc_mutex_var_val`
--
ALTER TABLE `rpcc_mutex_var_val`
  ADD CONSTRAINT `rpcc_mutex_var_val_ibfk_1` FOREIGN KEY (`var`) REFERENCES `rpcc_mutex_var` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `rpcc_result_int`
--
ALTER TABLE `rpcc_result_int`
  ADD CONSTRAINT `rpcc_result_int_ibfk_1` FOREIGN KEY (`resid`) REFERENCES `rpcc_result` (`resid`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `rpcc_result_string`
--
ALTER TABLE `rpcc_result_string`
  ADD CONSTRAINT `rpcc_result_string_ibfk_1` FOREIGN KEY (`resid`) REFERENCES `rpcc_result` (`resid`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `rpcc_session_string`
--
ALTER TABLE `rpcc_session_string`
  ADD CONSTRAINT `rpcc_session_string_ibfk_1` FOREIGN KEY (`session_id`) REFERENCES `rpcc_session` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `str_option`
--
ALTER TABLE `str_option`
  ADD CONSTRAINT `str_option_ibfk_1` FOREIGN KEY (`option_base`) REFERENCES `option_base` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `subnetworks`
--
ALTER TABLE `subnetworks`
  ADD CONSTRAINT `subnetworks_ibfk_1` FOREIGN KEY (`network`) REFERENCES `networks` (`id`) ON UPDATE CASCADE,
  ADD CONSTRAINT `subnetworks_ibfk_2` FOREIGN KEY (`optionset`) REFERENCES `optionset` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

