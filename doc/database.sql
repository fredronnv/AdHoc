
-- Generation Time: Nov 21, 2013 at 03:14 PM
-- Server version: 5.0.95

SET SQL_MODE="NO_AUTO_VALUE_ON_ZERO";

--
-- Database: `AdHoc`
--

-- --------------------------------------------------------

--
-- Table structure for table `buildings`
--

CREATE TABLE IF NOT EXISTS `buildings` (
  `id` varchar(24) collate utf8_bin NOT NULL COMMENT 'Building id',
  `re` varchar(64) collate utf8_bin NOT NULL COMMENT 'Regex to match room codes for this building',
  `info` varchar(128) collate utf8_bin NOT NULL COMMENT 'building information',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'time of last change',
  PRIMARY KEY  (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Buildings table';


-- --------------------------------------------------------

--
-- Table structure for table `classes`
--

CREATE TABLE IF NOT EXISTS `classes` (
  `classname` varchar(64) collate utf8_bin NOT NULL COMMENT 'Name of class',
  `optionspace` varchar(16) character set ascii collate ascii_bin default NULL COMMENT 'Option space, if any',
  `vendor_class_id` varchar(32) character set ascii collate ascii_bin default NULL COMMENT 'Data for vendor class id stmt',
  `info` varchar(80) collate utf8_bin default NULL COMMENT 'Class description',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  PRIMARY KEY  (`classname`),
  KEY `optionspace` (`optionspace`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Table of classes';


-- --------------------------------------------------------

--
-- Table structure for table `class_literal_options`
--

CREATE TABLE IF NOT EXISTS `class_literal_options` (
  `for` varchar(64) collate utf8_bin NOT NULL COMMENT 'Class on which to apply this option',
  `value` varchar(256) collate utf8_bin NOT NULL COMMENT 'Option value',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  KEY `for` (`for`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Literal options for classes';


-- --------------------------------------------------------

--
-- Table structure for table `class_options`
--

CREATE TABLE IF NOT EXISTS `class_options` (
  `for` varchar(64) collate utf8_bin NOT NULL COMMENT 'Class on which to apply the option',
  `name` varchar(32) character set ascii collate ascii_bin NOT NULL COMMENT 'Option name',
  `value` varchar(640) collate utf8_bin NOT NULL COMMENT 'The value of the option',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `id` int(10) unsigned NOT NULL auto_increment COMMENT 'Internal id',
  PRIMARY KEY  (`id`),
  KEY `for` (`for`),
  KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Option list for classes' AUTO_INCREMENT=1 ;



-- --------------------------------------------------------

--
-- Table structure for table `dhcp_servers`
--

CREATE TABLE IF NOT EXISTS `dhcp_servers` (
  `name` varchar(32) character set ascii collate ascii_bin NOT NULL COMMENT 'DNS name of server',
  `info` varchar(80) collate utf8_bin NOT NULL COMMENT 'Server description',
  `id` char(1) collate utf8_bin NOT NULL COMMENT 'DHCP server id',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  PRIMARY KEY  (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Table of classes';



-- --------------------------------------------------------

--
-- Table structure for table `global_options`
--

CREATE TABLE IF NOT EXISTS `global_options` (
  `name` varchar(32) character set ascii collate ascii_bin NOT NULL,
  `value` varchar(1024) collate utf8_bin NOT NULL,
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL,
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
  `id` int(10) unsigned NOT NULL auto_increment,
  PRIMARY KEY  (`id`),
  KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Table holding options global to the servers' AUTO_INCREMENT=1 ;




-- --------------------------------------------------------

--
-- Table structure for table `groups`
--

CREATE TABLE IF NOT EXISTS `groups` (
  `groupname` varchar(64) collate utf8_bin NOT NULL COMMENT 'Group name',
  `optionspace` varchar(16) character set ascii collate ascii_bin default NULL COMMENT 'Option space',
  `parent_group` varchar(64) collate utf8_bin NOT NULL COMMENT 'Parent group',
  `info` varchar(80) collate utf8_bin default NULL COMMENT 'Information on the group',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  PRIMARY KEY  (`groupname`),
  KEY `optionspace` (`optionspace`),
  KEY `parent_group` (`parent_group`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Table of classes';

--
-- Dumping data for table `groups`
--

INSERT INTO `groups` (`groupname`, `optionspace`, `parent_group`, `info`, `changed_by`, `mtime`) VALUES('plain', NULL, 'plain', 'This is the root of all groups', 'bernerus', '2013-11-21 11:14:45');

-- --------------------------------------------------------

--
-- Table structure for table `group_literal_options`
--

CREATE TABLE IF NOT EXISTS `group_literal_options` (
  `for` varchar(64) collate utf8_bin NOT NULL COMMENT 'Group on which to apply this option',
  `value` varchar(256) collate utf8_bin NOT NULL COMMENT 'Option value',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  KEY `for` (`for`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Literal options for groups';



-- --------------------------------------------------------

--
-- Table structure for table `group_options`
--

CREATE TABLE IF NOT EXISTS `group_options` (
  `for` varchar(64) collate utf8_bin NOT NULL COMMENT 'Group on which to apply the option',
  `name` varchar(32) character set ascii collate ascii_bin NOT NULL COMMENT 'Option name',
  `value` varchar(640) collate utf8_bin NOT NULL COMMENT 'The value of the option',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `id` int(10) unsigned NOT NULL auto_increment COMMENT 'Internal id',
  PRIMARY KEY  (`id`),
  KEY `for` (`for`),
  KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Option list for groups' AUTO_INCREMENT=1 ;



-- --------------------------------------------------------

--
-- Table structure for table `hosts`
--

CREATE TABLE IF NOT EXISTS `hosts` (
  `id` varchar(64) collate utf8_bin NOT NULL COMMENT 'Host ID',
  `dns` varchar(64) character set ascii collate ascii_bin NOT NULL default 'localhost' COMMENT 'DNS name',
  `group` varchar(64) collate utf8_bin default 'plain' COMMENT 'Group where the host belongs',
  `mac` varchar(17) character set ascii collate ascii_bin NOT NULL default '00:00:00:00:00:00' COMMENT 'Mac address',
  `room` varchar(10) collate utf8_bin default NULL COMMENT 'Room code',
  `optionspace` varchar(16) character set ascii collate ascii_bin default NULL COMMENT 'Option space to define',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `info` varchar(80) collate utf8_bin default NULL COMMENT 'Host comment',
  `entry_status` varchar(8) character set ascii collate ascii_bin NOT NULL default 'Active',
  PRIMARY KEY  (`id`),
  KEY `dns` (`dns`),
  KEY `group` (`group`),
  KEY `mac` (`mac`),
  KEY `entry_status` (`entry_status`),
  KEY `room` (`room`),
  KEY `optionspace` (`optionspace`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='List of hosts';




-- --------------------------------------------------------

--
-- Table structure for table `host_literal_options`
--

CREATE TABLE IF NOT EXISTS `host_literal_options` (
  `for` varchar(64) collate utf8_bin NOT NULL COMMENT 'Host on which to apply this option',
  `value` varchar(256) collate utf8_bin NOT NULL COMMENT 'Option value',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  KEY `for` (`for`),
  KEY `value` (`value`(255))
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Literal options for hosts';




-- --------------------------------------------------------

--
-- Table structure for table `host_options`
--

CREATE TABLE IF NOT EXISTS `host_options` (
  `for` varchar(64) collate utf8_bin NOT NULL COMMENT 'Host on which to apply the option',
  `name` varchar(32) character set ascii collate ascii_bin NOT NULL COMMENT 'Option name',
  `value` varchar(640) collate utf8_bin NOT NULL COMMENT 'The value of the option',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `id` int(10) unsigned NOT NULL auto_increment COMMENT 'Internal id',
  PRIMARY KEY  (`id`),
  KEY `for` (`for`),
  KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Option list for hosts' AUTO_INCREMENT=1 ;




-- --------------------------------------------------------

--
-- Table structure for table `networks`
--

CREATE TABLE IF NOT EXISTS `networks` (
  `id` varchar(64) collate utf8_bin NOT NULL COMMENT 'Name of network',
  `authoritative` int(1) NOT NULL default '1' COMMENT 'Whether the network is authoritative or nor',
  `info` varchar(80) collate utf8_bin default NULL COMMENT 'Network description',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  PRIMARY KEY  (`id`),
  KEY `optionspace` (`authoritative`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Table of classes';




-- --------------------------------------------------------

--
-- Table structure for table `network_options`
--

CREATE TABLE IF NOT EXISTS `network_options` (
  `for` varchar(64) collate utf8_bin NOT NULL COMMENT 'Network on which to apply the option',
  `name` varchar(32) character set ascii collate ascii_bin NOT NULL COMMENT 'Option name',
  `value` varchar(640) collate utf8_bin NOT NULL COMMENT 'The value of the option',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `id` int(10) unsigned NOT NULL auto_increment COMMENT 'Internal id',
  PRIMARY KEY  (`id`),
  KEY `for` (`for`),
  KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Option list for networks' AUTO_INCREMENT=1 ;




-- --------------------------------------------------------

--
-- Table structure for table `optionspaces`
--

CREATE TABLE IF NOT EXISTS `optionspaces` (
  `id` int(11) NOT NULL auto_increment COMMENT 'Id of option space',
  `value` varchar(16) character set ascii collate ascii_bin NOT NULL COMMENT 'Option space name',
  `type` enum('vendor','site') character set ascii collate ascii_bin NOT NULL COMMENT 'Vendor or site space',
  `info` varchar(80) collate utf8_bin default NULL COMMENT 'Class description',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  PRIMARY KEY  (`id`),
  KEY `value` (`value`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Table of classes' AUTO_INCREMENT=1 ;




-- --------------------------------------------------------

--
-- Table structure for table `option_defs`
--

CREATE TABLE IF NOT EXISTS `option_defs` (
  `id` int(11) NOT NULL auto_increment COMMENT 'Id of option space',
  `name` varchar(32) character set ascii collate ascii_bin NOT NULL COMMENT 'Option name',
  `code` int(3) NOT NULL COMMENT 'Numeric code in DHCP protocol',
  `qualifier` enum('array','parameter','parameter-array') character set ascii collate ascii_bin default NULL COMMENT 'Adjustments to the option. Array and/or parameter. A parameter is a standard DHSP option defined here.',
  `type` enum('ip-address','text','unsigned integer 8','unsigned integer 16','unsigned integer 32','integer 8','integer 16','integer 32','string','boolean') character set ascii collate ascii_bin NOT NULL default 'text' COMMENT 'Option''s basic type',
  `optionspace` varchar(16) character set ascii collate ascii_bin default NULL COMMENT 'Optionspace that has to be defined to use this option, if any.',
  `encapsulate` varchar(16) character set ascii collate ascii_bin default NULL COMMENT 'The option space that is to be encapsulated by this option, if any.',
  `struct` varchar(1024) character set ascii collate ascii_bin default NULL COMMENT 'The option is a record defined by the structure definition given here.',
  `info` varchar(80) collate utf8_bin default NULL COMMENT 'Class description',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  PRIMARY KEY  (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `optionspace` (`optionspace`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Table of classes' AUTO_INCREMENT=1 ;



-- --------------------------------------------------------

--
-- Table structure for table `pools`
--

CREATE TABLE IF NOT EXISTS `pools` (
  `poolname` varchar(64) collate utf8_bin NOT NULL COMMENT 'Name of pool',
  `optionspace` varchar(16) character set ascii collate ascii_bin default NULL COMMENT 'Option space, if any',
  `network` varchar(64) collate utf8_bin default NULL COMMENT 'Network the pool belongs to',
  `info` varchar(80) collate utf8_bin default NULL COMMENT 'Pool description',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  PRIMARY KEY  (`poolname`),
  KEY `optionspace` (`optionspace`),
  KEY `network` (`network`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Table of classes';



-- --------------------------------------------------------

--
-- Table structure for table `pool_literal_options`
--

CREATE TABLE IF NOT EXISTS `pool_literal_options` (
  `for` varchar(64) collate utf8_bin NOT NULL COMMENT 'Pool on which to apply this option',
  `value` varchar(256) collate utf8_bin NOT NULL COMMENT 'Option value',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  KEY `for` (`for`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Literal options for pools';




-- --------------------------------------------------------

--
-- Table structure for table `pool_map`
--

CREATE TABLE IF NOT EXISTS `pool_map` (
  `pool` varchar(64) collate utf8_bin NOT NULL COMMENT 'Pool where the host may live',
  `host` varchar(64) collate utf8_bin NOT NULL COMMENT 'Host id',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  KEY `value` (`host`),
  KEY `host` (`pool`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Defines which hosts may live in which pools';



-- --------------------------------------------------------

--
-- Table structure for table `pool_options`
--

CREATE TABLE IF NOT EXISTS `pool_options` (
  `for` varchar(64) collate utf8_bin NOT NULL COMMENT 'Pool on which to apply the option',
  `name` varchar(32) character set ascii collate ascii_bin NOT NULL COMMENT 'Option name',
  `value` varchar(640) collate utf8_bin NOT NULL COMMENT 'The value of the option',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `id` int(10) unsigned NOT NULL auto_increment COMMENT 'Internal id',
  PRIMARY KEY  (`id`),
  KEY `for` (`for`),
  KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Option list for pools' AUTO_INCREMENT=1 ;


-- --------------------------------------------------------

--
-- Table structure for table `pool_ranges`
--

CREATE TABLE IF NOT EXISTS `pool_ranges` (
  `pool` varchar(64) collate utf8_bin NOT NULL COMMENT 'Name of pool this range belongs to',
  `start_ip` varchar(15) character set ascii collate ascii_bin NOT NULL COMMENT 'First IP of range',
  `end_ip` varchar(15) character set ascii collate ascii_bin NOT NULL COMMENT 'Last IP of range',
  `served_by` char(1) collate utf8_bin NOT NULL default 'A' COMMENT 'DHCP server serving this range',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  UNIQUE KEY `start_ip` (`start_ip`),
  UNIQUE KEY `end_ip` (`end_ip`),
  UNIQUE KEY `start_ip_2` (`start_ip`,`end_ip`),
  KEY `pool` (`pool`),
  KEY `served_by` (`served_by`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Table of classes';



-- --------------------------------------------------------

--
-- Table structure for table `rooms`
--

CREATE TABLE IF NOT EXISTS `rooms` (
  `id` varchar(8) collate utf8_bin NOT NULL COMMENT 'Room ID',
  `info` varchar(80) collate utf8_bin default NULL COMMENT 'Room description',
  `printer` varchar(1024) collate utf8_bin default NULL COMMENT 'Printer list, if any',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'time of last change',
  PRIMARY KEY  (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='List of defined rooms';



-- --------------------------------------------------------

--
-- Table structure for table `subnetworks`
--

CREATE TABLE IF NOT EXISTS `subnetworks` (
  `id` varchar(15) character set ascii collate ascii_bin NOT NULL default '129.16.' COMMENT 'First IP of subnetwork',
  `network` varchar(64) collate utf8_bin default NULL COMMENT 'Network the subnetwork belongs to',
  `info` varchar(80) collate utf8_bin default NULL COMMENT 'Subnetwork description',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  PRIMARY KEY  (`id`),
  KEY `network` (`network`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Table of classes';



-- --------------------------------------------------------

--
-- Table structure for table `subnetwork_options`
--

CREATE TABLE IF NOT EXISTS `subnetwork_options` (
  `for` varchar(15) character set ascii collate ascii_bin NOT NULL COMMENT 'Subnetwork on which to apply the option',
  `name` varchar(32) character set ascii collate ascii_bin NOT NULL COMMENT 'Option name',
  `value` varchar(640) collate utf8_bin NOT NULL COMMENT 'The value of the option',
  `changed_by` varchar(8) character set ascii collate ascii_bin NOT NULL COMMENT 'Cid of last changer',
  `mtime` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP COMMENT 'Time of last change',
  `id` int(10) unsigned NOT NULL auto_increment COMMENT 'Internal id',
  PRIMARY KEY  (`id`),
  KEY `for` (`for`),
  KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='Option list for subnetworks' AUTO_INCREMENT=1 ;


--
-- Constraints for table `classes`
--
ALTER TABLE `classes`
  ADD CONSTRAINT `classes_ibfk_1` FOREIGN KEY (`optionspace`) REFERENCES `optionspaces` (`value`) ON UPDATE CASCADE;

--
-- Constraints for table `class_literal_options`
--
ALTER TABLE `class_literal_options`
  ADD CONSTRAINT `class_literal_options_ibfk_1` FOREIGN KEY (`for`) REFERENCES `classes` (`classname`) ON UPDATE CASCADE;

--
-- Constraints for table `class_options`
--
ALTER TABLE `class_options`
  ADD CONSTRAINT `class_options_ibfk_2` FOREIGN KEY (`name`) REFERENCES `option_defs` (`name`),
  ADD CONSTRAINT `class_options_ibfk_1` FOREIGN KEY (`for`) REFERENCES `classes` (`classname`) ON UPDATE CASCADE;

--
-- Constraints for table `groups`
--
ALTER TABLE `groups`
  ADD CONSTRAINT `groups_ibfk_3` FOREIGN KEY (`parent_group`) REFERENCES `groups` (`groupname`) ON UPDATE CASCADE,
  ADD CONSTRAINT `groups_ibfk_2` FOREIGN KEY (`optionspace`) REFERENCES `optionspaces` (`value`) ON UPDATE CASCADE;

--
-- Constraints for table `group_literal_options`
--
ALTER TABLE `group_literal_options`
  ADD CONSTRAINT `group_literal_options_ibfk_1` FOREIGN KEY (`for`) REFERENCES `groups` (`groupname`);

--
-- Constraints for table `group_options`
--
ALTER TABLE `group_options`
  ADD CONSTRAINT `group_options_ibfk_2` FOREIGN KEY (`name`) REFERENCES `option_defs` (`name`) ON UPDATE CASCADE,
  ADD CONSTRAINT `group_options_ibfk_1` FOREIGN KEY (`for`) REFERENCES `groups` (`groupname`) ON UPDATE CASCADE;

--
-- Constraints for table `hosts`
--
ALTER TABLE `hosts`
  ADD CONSTRAINT `hosts_ibfk_8` FOREIGN KEY (`optionspace`) REFERENCES `optionspaces` (`value`) ON UPDATE CASCADE,
  ADD CONSTRAINT `hosts_ibfk_6` FOREIGN KEY (`group`) REFERENCES `groups` (`groupname`) ON UPDATE CASCADE,
  ADD CONSTRAINT `hosts_ibfk_7` FOREIGN KEY (`room`) REFERENCES `rooms` (`id`) ON UPDATE CASCADE;

--
-- Constraints for table `host_literal_options`
--
ALTER TABLE `host_literal_options`
  ADD CONSTRAINT `host_literal_options_ibfk_1` FOREIGN KEY (`for`) REFERENCES `hosts` (`id`) ON UPDATE CASCADE;

--
-- Constraints for table `host_options`
--
ALTER TABLE `host_options`
  ADD CONSTRAINT `host_options_ibfk_2` FOREIGN KEY (`name`) REFERENCES `option_defs` (`name`) ON UPDATE CASCADE,
  ADD CONSTRAINT `host_options_ibfk_1` FOREIGN KEY (`for`) REFERENCES `hosts` (`id`) ON UPDATE CASCADE;

--
-- Constraints for table `network_options`
--
ALTER TABLE `network_options`
  ADD CONSTRAINT `network_options_ibfk_4` FOREIGN KEY (`name`) REFERENCES `option_defs` (`name`) ON UPDATE CASCADE,
  ADD CONSTRAINT `network_options_ibfk_3` FOREIGN KEY (`for`) REFERENCES `networks` (`id`) ON UPDATE CASCADE;

--
-- Constraints for table `option_defs`
--
ALTER TABLE `option_defs`
  ADD CONSTRAINT `option_defs_ibfk_1` FOREIGN KEY (`optionspace`) REFERENCES `optionspaces` (`value`) ON UPDATE CASCADE;

--
-- Constraints for table `pools`
--
ALTER TABLE `pools`
  ADD CONSTRAINT `pools_ibfk_2` FOREIGN KEY (`network`) REFERENCES `networks` (`id`) ON UPDATE CASCADE,
  ADD CONSTRAINT `pools_ibfk_1` FOREIGN KEY (`optionspace`) REFERENCES `optionspaces` (`value`) ON UPDATE CASCADE;

--
-- Constraints for table `pool_literal_options`
--
ALTER TABLE `pool_literal_options`
  ADD CONSTRAINT `pool_literal_options_ibfk_1` FOREIGN KEY (`for`) REFERENCES `pools` (`poolname`) ON UPDATE CASCADE;

--
-- Constraints for table `pool_map`
--
ALTER TABLE `pool_map`
  ADD CONSTRAINT `pool_map_ibfk_2` FOREIGN KEY (`host`) REFERENCES `hosts` (`id`) ON UPDATE CASCADE,
  ADD CONSTRAINT `pool_map_ibfk_1` FOREIGN KEY (`pool`) REFERENCES `pools` (`poolname`) ON UPDATE CASCADE;

--
-- Constraints for table `pool_options`
--
ALTER TABLE `pool_options`
  ADD CONSTRAINT `pool_options_ibfk_2` FOREIGN KEY (`name`) REFERENCES `option_defs` (`name`) ON UPDATE CASCADE,
  ADD CONSTRAINT `pool_options_ibfk_1` FOREIGN KEY (`for`) REFERENCES `pools` (`poolname`) ON UPDATE CASCADE;

--
-- Constraints for table `pool_ranges`
--
ALTER TABLE `pool_ranges`
  ADD CONSTRAINT `pool_ranges_ibfk_2` FOREIGN KEY (`served_by`) REFERENCES `dhcp_servers` (`id`) ON UPDATE CASCADE,
  ADD CONSTRAINT `pool_ranges_ibfk_1` FOREIGN KEY (`pool`) REFERENCES `pools` (`poolname`) ON UPDATE CASCADE;

--
-- Constraints for table `subnetworks`
--
ALTER TABLE `subnetworks`
  ADD CONSTRAINT `subnetworks_ibfk_1` FOREIGN KEY (`network`) REFERENCES `networks` (`id`) ON UPDATE CASCADE;

--
-- Constraints for table `subnetwork_options`
--
ALTER TABLE `subnetwork_options`
  ADD CONSTRAINT `subnetwork_options_ibfk_3` FOREIGN KEY (`name`) REFERENCES `option_defs` (`name`) ON UPDATE CASCADE,
  ADD CONSTRAINT `subnetwork_options_ibfk_2` FOREIGN KEY (`for`) REFERENCES `subnetworks` (`id`) ON UPDATE CASCADE;
