-- phpMyAdmin SQL Dump
-- version 2.11.6
-- http://www.phpmyadmin.net
--
-- Host: dconf.ita.chalmers.se
-- Generation Time: Feb 27, 2014 at 09:16 PM
-- Server version: 5.0.95
-- PHP Version: 5.1.4

SET SQL_MODE="NO_AUTO_VALUE_ON_ZERO";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;

--
-- Database: `AdHoc`
--

-- --------------------------------------------------------

--
-- Table structure for table `bool_option`
--

CREATE TABLE IF NOT EXISTS `bool_option` (
  `id` int(11) NOT NULL auto_increment,
  `option_base` int(11) NOT NULL,
  PRIMARY KEY  (`id`),
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
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'time of last change',
  PRIMARY KEY  (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Buildings table';

-- --------------------------------------------------------

--
-- Table structure for table `classes`
--

CREATE TABLE IF NOT EXISTS `classes` (
  `classname` varchar(64) NOT NULL COMMENT 'Name of class',
  `optionspace` varchar(16) character set ascii collate ascii_bin default NULL COMMENT 'Option space, if any',
  `vendor_class_id` varchar(32) character set ascii collate ascii_bin default NULL COMMENT 'Data for vendor class id stmt',
  `info` varchar(80) default NULL COMMENT 'Class description',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `optionset` int(11) NOT NULL,
  PRIMARY KEY  (`classname`),
  KEY `optionspace` (`optionspace`),
  KEY `optionset` (`optionset`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Table of classes';

-- --------------------------------------------------------

--
-- Table structure for table `class_literal_options`
--

CREATE TABLE IF NOT EXISTS `class_literal_options` (
  `for` varchar(64) NOT NULL COMMENT 'Class on which to apply this option',
  `value` varchar(256) NOT NULL COMMENT 'Option value',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `id` int(11) NOT NULL auto_increment,
  PRIMARY KEY  (`id`),
  KEY `for` (`for`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 COMMENT='Literal options for classes' AUTO_INCREMENT=4 ;

-- --------------------------------------------------------

--
-- Table structure for table `dhcp_servers`
--

CREATE TABLE IF NOT EXISTS `dhcp_servers` (
  `name` varchar(32) character set ascii collate ascii_bin NOT NULL COMMENT 'DNS name of server',
  `info` varchar(80) NOT NULL COMMENT 'Server description',
  `id` char(1) NOT NULL COMMENT 'DHCP server id',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  PRIMARY KEY  (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='List of dhcp servers';

-- --------------------------------------------------------

--
-- Table structure for table `global_options`
--

CREATE TABLE IF NOT EXISTS `global_options` (
  `name` varchar(32) character set ascii collate ascii_bin NOT NULL,
  `value` varchar(1024) NOT NULL,
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL,
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
  `id` int(10) unsigned NOT NULL auto_increment,
  PRIMARY KEY  (`id`),
  KEY `name` (`name`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 COMMENT='Table holding options global to the servers' AUTO_INCREMENT=1465 ;

-- --------------------------------------------------------

--
-- Table structure for table `groups`
--

CREATE TABLE IF NOT EXISTS `groups` (
  `groupname` varchar(64) NOT NULL COMMENT 'Group name',
  `optionspace` varchar(16) character set ascii collate ascii_bin default NULL COMMENT 'Option space',
  `parent_group` varchar(64) NOT NULL COMMENT 'Parent group',
  `info` varchar(80) default NULL COMMENT 'Information on the group',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `optionset` int(11) NOT NULL,
  PRIMARY KEY  (`groupname`),
  KEY `optionspace` (`optionspace`),
  KEY `parent_group` (`parent_group`),
  KEY `optionset` (`optionset`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Table of host groups';

-- --------------------------------------------------------

--
-- Table structure for table `group_literal_options`
--

CREATE TABLE IF NOT EXISTS `group_literal_options` (
  `for` varchar(64) NOT NULL COMMENT 'Group on which to apply this option',
  `value` varchar(256) NOT NULL COMMENT 'Option value',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `id` int(11) NOT NULL auto_increment,
  PRIMARY KEY  (`id`),
  KEY `for` (`for`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 COMMENT='Literal options for groups' AUTO_INCREMENT=3 ;

-- --------------------------------------------------------

--
-- Table structure for table `hosts`
--

CREATE TABLE IF NOT EXISTS `hosts` (
  `id` varchar(64) NOT NULL COMMENT 'Host ID',
  `dns` varchar(255) character set ascii collate ascii_bin default 'localhost' COMMENT 'DNS name',
  `group` varchar(64) default 'plain' COMMENT 'Group where the host belongs',
  `mac` varchar(17) character set ascii collate ascii_bin NOT NULL default '00:00:00:00:00:00' COMMENT 'Mac address',
  `room` varchar(10) default NULL COMMENT 'Room code',
  `optionspace` varchar(16) character set ascii collate ascii_bin default NULL COMMENT 'Option space to define',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `info` varchar(80) default NULL COMMENT 'Host comment',
  `entry_status` varchar(8) character set ascii collate ascii_bin NOT NULL default 'Active',
  `optionset` int(11) NOT NULL,
  PRIMARY KEY  (`id`),
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
-- Table structure for table `host_literal_options`
--

CREATE TABLE IF NOT EXISTS `host_literal_options` (
  `for` varchar(64) NOT NULL COMMENT 'Host on which to apply this option',
  `value` varchar(256) NOT NULL COMMENT 'Option value',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `id` int(11) NOT NULL auto_increment,
  PRIMARY KEY  (`id`),
  KEY `for` (`for`),
  KEY `value` (`value`(255))
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Literal options for hosts' AUTO_INCREMENT=1 ;

-- --------------------------------------------------------

--
-- Table structure for table `int_option`
--

CREATE TABLE IF NOT EXISTS `int_option` (
  `id` int(11) NOT NULL auto_increment,
  `option_base` int(11) NOT NULL,
  `minval` int(11) default NULL,
  `maxval` int(11) default NULL,
  PRIMARY KEY  (`id`),
  KEY `option_base` (`option_base`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 AUTO_INCREMENT=21 ;

-- --------------------------------------------------------

--
-- Table structure for table `ipaddr_option`
--

CREATE TABLE IF NOT EXISTS `ipaddr_option` (
  `id` int(11) NOT NULL auto_increment,
  `option_base` int(11) NOT NULL,
  PRIMARY KEY  (`id`),
  KEY `option_base` (`option_base`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 AUTO_INCREMENT=20 ;

-- --------------------------------------------------------

--
-- Table structure for table `networks`
--

CREATE TABLE IF NOT EXISTS `networks` (
  `id` varchar(64) NOT NULL COMMENT 'Name of network',
  `authoritative` int(1) NOT NULL default '1' COMMENT 'Whether the network is authoritative or nor',
  `info` varchar(80) default NULL COMMENT 'Network description',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `optionset` int(11) NOT NULL,
  PRIMARY KEY  (`id`),
  KEY `optionspace` (`authoritative`),
  KEY `optionset` (`optionset`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Table of shared networks';

-- --------------------------------------------------------

--
-- Table structure for table `optionset`
--

CREATE TABLE IF NOT EXISTS `optionset` (
  `id` int(11) NOT NULL auto_increment,
  PRIMARY KEY  (`id`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 AUTO_INCREMENT=12342 ;

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
  `id` int(11) NOT NULL auto_increment COMMENT 'Id of option space',
  `value` varchar(16) character set ascii collate ascii_bin NOT NULL COMMENT 'Option space name',
  `type` enum('vendor','site') character set ascii collate ascii_bin NOT NULL COMMENT 'Vendor or site space',
  `info` varchar(80) default NULL COMMENT 'Class description',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  PRIMARY KEY  (`id`),
  UNIQUE KEY `value` (`value`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 COMMENT='Definitions of option spaces' AUTO_INCREMENT=14 ;

-- --------------------------------------------------------

--
-- Table structure for table `option_base`
--

CREATE TABLE IF NOT EXISTS `option_base` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(64) default NULL,
  `info` varchar(1024) default NULL,
  `guard` varchar(64) default NULL,
  `from_api` smallint(6) NOT NULL default '0',
  `to_api` smallint(6) NOT NULL default '10000',
  `code` int(3) default NULL COMMENT 'Numeric code in DHCP protocol',
  `qualifier` enum('array','parameter','parameter-array') character set ascii collate ascii_bin default NULL COMMENT 'Adjustments to the option. Array and/or parameter. A parameter is a standard DHSP option defined here.',
  `type` enum('ip-address','text','unsigned integer 8','unsigned integer 16','unsigned integer 32','integer 8','integer 16','integer 32','string','boolean') character set ascii collate ascii_bin NOT NULL default 'text',
  `optionspace` varchar(16) character set ascii collate ascii_bin default NULL COMMENT 'Optionspace that has to be defined to use this option, if any.',
  `encapsulate` varchar(16) character set ascii collate ascii_bin default NULL COMMENT 'The option space that is to be encapsulated by this option, if any.',
  `struct` varchar(1024) character set ascii collate ascii_bin default NULL COMMENT 'The option is a record defined by the structure definition given here.',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  PRIMARY KEY  (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `optionspace` (`optionspace`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 AUTO_INCREMENT=110 ;

-- --------------------------------------------------------

--
-- Table structure for table `pools`
--

CREATE TABLE IF NOT EXISTS `pools` (
  `poolname` varchar(64) NOT NULL COMMENT 'Name of pool',
  `optionspace` varchar(16) character set ascii collate ascii_bin default NULL COMMENT 'Option space, if any',
  `max_lease_time` int(32) NOT NULL default '600',
  `network` varchar(64) default NULL COMMENT 'Network the pool belongs to',
  `info` varchar(80) default NULL COMMENT 'Pool description',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `optionset` int(11) NOT NULL,
  PRIMARY KEY  (`poolname`),
  KEY `optionspace` (`optionspace`),
  KEY `network` (`network`),
  KEY `optionset` (`optionset`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Table of pools';

-- --------------------------------------------------------

--
-- Table structure for table `pool_class_map`
--

CREATE TABLE IF NOT EXISTS `pool_class_map` (
  `poolname` varchar(64) NOT NULL COMMENT 'Pool where the host may live',
  `classname` varchar(64) NOT NULL COMMENT 'Class name',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
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
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  KEY `groupname` (`groupname`),
  KEY `poolname` (`poolname`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Defines which groups that may live in which pools';

-- --------------------------------------------------------

--
-- Table structure for table `pool_literal_options`
--

CREATE TABLE IF NOT EXISTS `pool_literal_options` (
  `for` varchar(64) NOT NULL COMMENT 'Pool on which to apply this option',
  `value` varchar(256) NOT NULL COMMENT 'Option value',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `id` int(11) NOT NULL auto_increment,
  PRIMARY KEY  (`id`),
  KEY `for` (`for`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Literal options for pools' AUTO_INCREMENT=1 ;

-- --------------------------------------------------------

--
-- Table structure for table `pool_ranges`
--

CREATE TABLE IF NOT EXISTS `pool_ranges` (
  `id` int(11) NOT NULL auto_increment,
  `pool` varchar(64) NOT NULL COMMENT 'Name of pool this range belongs to',
  `start_ip` varchar(15) character set ascii collate ascii_bin NOT NULL COMMENT 'First IP of range',
  `end_ip` varchar(15) character set ascii collate ascii_bin NOT NULL COMMENT 'Last IP of range',
  `served_by` char(1) NOT NULL default 'A' COMMENT 'DHCP server serving this range',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  PRIMARY KEY  (`id`),
  UNIQUE KEY `start_ip` (`start_ip`),
  UNIQUE KEY `end_ip` (`end_ip`),
  UNIQUE KEY `start_ip_2` (`start_ip`,`end_ip`),
  KEY `pool` (`pool`),
  KEY `served_by` (`served_by`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 COMMENT='Table IP ranges for pools' AUTO_INCREMENT=14 ;

-- --------------------------------------------------------

--
-- Table structure for table `rooms`
--

CREATE TABLE IF NOT EXISTS `rooms` (
  `id` varchar(10) NOT NULL COMMENT 'Room ID',
  `info` varchar(80) default NULL COMMENT 'Room description',
  `printers` varchar(1024) default NULL COMMENT 'Printer list, if any',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'time of last change',
  PRIMARY KEY  (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='List of defined rooms';

-- --------------------------------------------------------

--
-- Table structure for table `rpcc_api_version`
--

CREATE TABLE IF NOT EXISTS `rpcc_api_version` (
  `version` int(11) NOT NULL,
  `state` char(1) NOT NULL,
  `comment` varchar(2048) default NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `rpcc_event`
--

CREATE TABLE IF NOT EXISTS `rpcc_event` (
  `id` int(11) NOT NULL auto_increment,
  `typ` int(11) NOT NULL,
  `created` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
  `parent` int(11) default NULL,
  PRIMARY KEY  (`id`),
  KEY `parent` (`parent`),
  KEY `created` (`created`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;

-- --------------------------------------------------------

--
-- Table structure for table `rpcc_event_int`
--

CREATE TABLE IF NOT EXISTS `rpcc_event_int` (
  `event` int(11) NOT NULL,
  `attr` int(11) NOT NULL,
  `value` int(11) default NULL,
  UNIQUE KEY `rpcc_idx_evint` (`event`,`attr`),
  KEY `attr` (`attr`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `rpcc_event_int_attr`
--

CREATE TABLE IF NOT EXISTS `rpcc_event_int_attr` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(32) character set latin1 NOT NULL,
  PRIMARY KEY  (`id`),
  UNIQUE KEY `rpcc_idx_evintattr_name` (`name`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 AUTO_INCREMENT=4 ;

-- --------------------------------------------------------

--
-- Table structure for table `rpcc_event_str`
--

CREATE TABLE IF NOT EXISTS `rpcc_event_str` (
  `event` int(11) NOT NULL,
  `attr` int(11) NOT NULL,
  `value` varchar(2000) character set latin1 default NULL,
  UNIQUE KEY `rpcc_idx_evstr` (`event`,`attr`),
  KEY `attr` (`attr`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `rpcc_event_str_attr`
--

CREATE TABLE IF NOT EXISTS `rpcc_event_str_attr` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(32) character set latin1 NOT NULL,
  PRIMARY KEY  (`id`),
  UNIQUE KEY `rpcc_idx_evstrattr_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;

-- --------------------------------------------------------

--
-- Table structure for table `rpcc_event_type`
--

CREATE TABLE IF NOT EXISTS `rpcc_event_type` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(32) character set latin1 NOT NULL,
  PRIMARY KEY  (`id`),
  UNIQUE KEY `rpcc_idx_evtype` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;

-- --------------------------------------------------------

--
-- Table structure for table `rpcc_mutex`
--

CREATE TABLE IF NOT EXISTS `rpcc_mutex` (
  `id` int(11) NOT NULL auto_increment COMMENT 'Mutex id',
  `name` varchar(64) collate ascii_bin NOT NULL COMMENT 'Mutex name',
  `holder_session` varchar(40) collate ascii_bin NOT NULL COMMENT 'Session of holder',
  `holder_public` varchar(128) character set utf8 collate utf8_bin NOT NULL COMMENT 'Public name of holder',
  `last_change` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `forced` char(1) collate ascii_bin NOT NULL COMMENT 'Whether stolen or not. (Y/N)',
  PRIMARY KEY  (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin COMMENT='Rpcc Mutex list' AUTO_INCREMENT=1 ;

-- --------------------------------------------------------

--
-- Table structure for table `rpcc_mutex_var`
--

CREATE TABLE IF NOT EXISTS `rpcc_mutex_var` (
  `id` int(11) NOT NULL auto_increment,
  `mutex_id` int(11) NOT NULL,
  `name` varchar(64) collate ascii_bin NOT NULL,
  `collection` char(1) collate ascii_bin NOT NULL,
  PRIMARY KEY  (`id`),
  UNIQUE KEY `mutex_id_2` (`mutex_id`,`name`),
  KEY `mutex_id` (`mutex_id`)
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin COMMENT='Table holding mutex variables' AUTO_INCREMENT=1 ;

-- --------------------------------------------------------

--
-- Table structure for table `rpcc_mutex_var_val`
--

CREATE TABLE IF NOT EXISTS `rpcc_mutex_var_val` (
  `var` int(11) NOT NULL COMMENT 'ref to variable',
  `value` varchar(256) character set utf8 collate utf8_bin NOT NULL COMMENT 'Value of variable',
  KEY `var` (`var`)
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin COMMENT='Rpcc mutex variable values';

-- --------------------------------------------------------

--
-- Table structure for table `rpcc_result`
--

CREATE TABLE IF NOT EXISTS `rpcc_result` (
  `resid` int(11) NOT NULL COMMENT 'Result identifier',
  `manager` varchar(32) collate ascii_bin NOT NULL COMMENT 'Reference to the code that is supposed to handle the result.',
  `expires` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time when result can be deleted.',
  PRIMARY KEY  (`resid`)
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin COMMENT='Table for search result sets';

-- --------------------------------------------------------

--
-- Table structure for table `rpcc_result_int`
--

CREATE TABLE IF NOT EXISTS `rpcc_result_int` (
  `resid` int(11) NOT NULL COMMENT 'Reference to resultset',
  `value` int(11) default NULL COMMENT 'An integer value in the result set',
  KEY `resid` (`resid`)
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin COMMENT='Results that are integers, per result ID';

-- --------------------------------------------------------

--
-- Table structure for table `rpcc_result_string`
--

CREATE TABLE IF NOT EXISTS `rpcc_result_string` (
  `resid` int(11) NOT NULL COMMENT 'Reference to resultset',
  `value` varchar(128) collate utf8_bin default NULL COMMENT 'A string value in the result set',
  KEY `resid` (`resid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Results that are strings, per result ID';

-- --------------------------------------------------------

--
-- Table structure for table `rpcc_session`
--

CREATE TABLE IF NOT EXISTS `rpcc_session` (
  `id` varchar(40) collate ascii_bin NOT NULL COMMENT 'Session key',
  `expires` timestamp NOT NULL default '0000-00-00 00:00:00' COMMENT 'Time whensession expires',
  PRIMARY KEY  (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin COMMENT='RPCC session management';

-- --------------------------------------------------------

--
-- Table structure for table `rpcc_session_string`
--

CREATE TABLE IF NOT EXISTS `rpcc_session_string` (
  `session_id` varchar(40) character set ascii collate ascii_bin NOT NULL COMMENT 'Reference to session ID',
  `name` varchar(30) character set ascii collate ascii_bin NOT NULL COMMENT 'Name of variable',
  `value` varchar(30) collate utf8_bin default NULL COMMENT 'Value of variable',
  KEY `session_id` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Table for storing data for a session';

-- --------------------------------------------------------

--
-- Table structure for table `str_option`
--

CREATE TABLE IF NOT EXISTS `str_option` (
  `id` int(11) NOT NULL auto_increment,
  `option_base` int(11) NOT NULL,
  `regexp_constraint` varchar(128) default NULL,
  PRIMARY KEY  (`id`),
  KEY `option_base` (`option_base`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 AUTO_INCREMENT=70 ;

-- --------------------------------------------------------

--
-- Table structure for table `subnetworks`
--

CREATE TABLE IF NOT EXISTS `subnetworks` (
  `id` varchar(18) character set ascii collate ascii_bin NOT NULL default '129.16/16' COMMENT 'First IP of subnetwork',
  `network` varchar(64) default NULL COMMENT 'Network the subnetwork belongs to',
  `info` varchar(80) default NULL COMMENT 'Subnetwork description',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `optionset` int(11) NOT NULL,
  PRIMARY KEY  (`id`),
  KEY `network` (`network`),
  KEY `optionset` (`optionset`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Table of sub-networks';

--
-- Constraints for dumped tables
--

--
-- Constraints for table `bool_option`
--
ALTER TABLE `bool_option`
  ADD CONSTRAINT `bool_option_ibfk_1` FOREIGN KEY (`option_base`) REFERENCES `option_base` (`id`);

--
-- Constraints for table `classes`
--
ALTER TABLE `classes`
  ADD CONSTRAINT `classes_ibfk_4` FOREIGN KEY (`optionset`) REFERENCES `optionset` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `classes_ibfk_3` FOREIGN KEY (`optionspace`) REFERENCES `optionspaces` (`value`) ON UPDATE CASCADE;

--
-- Constraints for table `class_literal_options`
--
ALTER TABLE `class_literal_options`
  ADD CONSTRAINT `class_literal_options_ibfk_1` FOREIGN KEY (`for`) REFERENCES `classes` (`classname`) ON UPDATE CASCADE;

--
-- Constraints for table `groups`
--
ALTER TABLE `groups`
  ADD CONSTRAINT `groups_ibfk_5` FOREIGN KEY (`optionset`) REFERENCES `optionset` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `groups_ibfk_3` FOREIGN KEY (`optionspace`) REFERENCES `optionspaces` (`value`) ON UPDATE CASCADE,
  ADD CONSTRAINT `groups_ibfk_4` FOREIGN KEY (`parent_group`) REFERENCES `groups` (`groupname`) ON UPDATE CASCADE;

--
-- Constraints for table `group_literal_options`
--
ALTER TABLE `group_literal_options`
  ADD CONSTRAINT `group_literal_options_ibfk_1` FOREIGN KEY (`for`) REFERENCES `groups` (`groupname`);

--
-- Constraints for table `hosts`
--
ALTER TABLE `hosts`
  ADD CONSTRAINT `hosts_ibfk_17` FOREIGN KEY (`optionspace`) REFERENCES `optionspaces` (`value`) ON UPDATE CASCADE,
  ADD CONSTRAINT `hosts_ibfk_15` FOREIGN KEY (`optionset`) REFERENCES `optionset` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `hosts_ibfk_16` FOREIGN KEY (`room`) REFERENCES `rooms` (`id`) ON UPDATE CASCADE;

--
-- Constraints for table `host_literal_options`
--
ALTER TABLE `host_literal_options`
  ADD CONSTRAINT `host_literal_options_ibfk_1` FOREIGN KEY (`for`) REFERENCES `hosts` (`id`) ON UPDATE CASCADE;

--
-- Constraints for table `int_option`
--
ALTER TABLE `int_option`
  ADD CONSTRAINT `int_option_ibfk_1` FOREIGN KEY (`option_base`) REFERENCES `option_base` (`id`);

--
-- Constraints for table `ipaddr_option`
--
ALTER TABLE `ipaddr_option`
  ADD CONSTRAINT `ipaddr_option_ibfk_1` FOREIGN KEY (`option_base`) REFERENCES `option_base` (`id`);

--
-- Constraints for table `networks`
--
ALTER TABLE `networks`
  ADD CONSTRAINT `networks_ibfk_1` FOREIGN KEY (`optionset`) REFERENCES `optionset` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `optionset_boolval`
--
ALTER TABLE `optionset_boolval`
  ADD CONSTRAINT `optionset_boolval_ibfk_4` FOREIGN KEY (`optionset`) REFERENCES `optionset` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `optionset_boolval_ibfk_3` FOREIGN KEY (`bool_option`) REFERENCES `bool_option` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `optionset_intval`
--
ALTER TABLE `optionset_intval`
  ADD CONSTRAINT `optionset_intval_ibfk_4` FOREIGN KEY (`optionset`) REFERENCES `optionset` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `optionset_intval_ibfk_3` FOREIGN KEY (`int_option`) REFERENCES `int_option` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `optionset_ipaddrval`
--
ALTER TABLE `optionset_ipaddrval`
  ADD CONSTRAINT `optionset_ipaddrval_ibfk_7` FOREIGN KEY (`optionset`) REFERENCES `optionset` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `optionset_ipaddrval_ibfk_6` FOREIGN KEY (`ipaddr_option`) REFERENCES `ipaddr_option` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `optionset_strval`
--
ALTER TABLE `optionset_strval`
  ADD CONSTRAINT `optionset_strval_ibfk_4` FOREIGN KEY (`optionset`) REFERENCES `optionset` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `optionset_strval_ibfk_3` FOREIGN KEY (`str_option`) REFERENCES `str_option` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `option_base`
--
ALTER TABLE `option_base`
  ADD CONSTRAINT `option_base_ibfk_1` FOREIGN KEY (`optionspace`) REFERENCES `optionspaces` (`value`) ON UPDATE CASCADE;

--
-- Constraints for table `pools`
--
ALTER TABLE `pools`
  ADD CONSTRAINT `pools_ibfk_5` FOREIGN KEY (`optionset`) REFERENCES `optionset` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `pools_ibfk_3` FOREIGN KEY (`optionspace`) REFERENCES `optionspaces` (`value`) ON UPDATE CASCADE,
  ADD CONSTRAINT `pools_ibfk_4` FOREIGN KEY (`network`) REFERENCES `networks` (`id`) ON UPDATE CASCADE;

--
-- Constraints for table `pool_class_map`
--
ALTER TABLE `pool_class_map`
  ADD CONSTRAINT `pool_class_map_ibfk_2` FOREIGN KEY (`classname`) REFERENCES `classes` (`classname`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `pool_class_map_ibfk_1` FOREIGN KEY (`poolname`) REFERENCES `pools` (`poolname`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `pool_group_map`
--
ALTER TABLE `pool_group_map`
  ADD CONSTRAINT `pool_group_map_ibfk_2` FOREIGN KEY (`groupname`) REFERENCES `groups` (`groupname`) ON UPDATE CASCADE,
  ADD CONSTRAINT `pool_group_map_ibfk_1` FOREIGN KEY (`poolname`) REFERENCES `pools` (`poolname`) ON UPDATE CASCADE;

--
-- Constraints for table `pool_literal_options`
--
ALTER TABLE `pool_literal_options`
  ADD CONSTRAINT `pool_literal_options_ibfk_1` FOREIGN KEY (`for`) REFERENCES `pools` (`poolname`) ON UPDATE CASCADE;

--
-- Constraints for table `pool_ranges`
--
ALTER TABLE `pool_ranges`
  ADD CONSTRAINT `pool_ranges_ibfk_1` FOREIGN KEY (`pool`) REFERENCES `pools` (`poolname`) ON UPDATE CASCADE,
  ADD CONSTRAINT `pool_ranges_ibfk_2` FOREIGN KEY (`served_by`) REFERENCES `dhcp_servers` (`id`) ON UPDATE CASCADE;

--
-- Constraints for table `rpcc_event_int`
--
ALTER TABLE `rpcc_event_int`
  ADD CONSTRAINT `rpcc_event_int_ibfk_2` FOREIGN KEY (`attr`) REFERENCES `rpcc_event_int_attr` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `rpcc_event_int_ibfk_1` FOREIGN KEY (`event`) REFERENCES `rpcc_event` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `rpcc_event_str`
--
ALTER TABLE `rpcc_event_str`
  ADD CONSTRAINT `rpcc_event_str_ibfk_2` FOREIGN KEY (`attr`) REFERENCES `rpcc_event_int_attr` (`id`),
  ADD CONSTRAINT `rpcc_event_str_ibfk_1` FOREIGN KEY (`event`) REFERENCES `rpcc_event` (`id`);

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
  ADD CONSTRAINT `str_option_ibfk_1` FOREIGN KEY (`option_base`) REFERENCES `option_base` (`id`);

--
-- Constraints for table `subnetworks`
--
ALTER TABLE `subnetworks`
  ADD CONSTRAINT `subnetworks_ibfk_2` FOREIGN KEY (`optionset`) REFERENCES `optionset` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `subnetworks_ibfk_1` FOREIGN KEY (`network`) REFERENCES `networks` (`id`) ON UPDATE CASCADE;
