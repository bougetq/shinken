#!/usr/bin/env python
# author:
#    Quentin Bouget, quentin.bouget.ocre@cea.fr
#
# This file is part of Shinken.
#
# This file is used to test reading and processing of config files
#

from shinken_test import ShinkenTest, unittest

SKIP_MESSAGE = "the nodesetparse module was not loaded properly, " +\
               "either your version of ClusterShell is not up to date " +\
               "or the latest version of ClusterShell.NodeSet broke " +\
               "nodesetparse implementation"
try:
    from shinken.objects.nodesetparse import process as nodeset_process
    SKIP = False
except ImportError:
    SKIP = True

@unittest.skipIf(SKIP, SKIP_MESSAGE)
class TestNodesetparse(ShinkenTest):

    def setUp(self):
        self.setup_with_file('etc/shinken_nodesetparse.cfg')
        self.assertTrue(self.conf.conf_is_correct,
                        "The configuration was deemed incorect")

    def hosts_from_name_list(self, name_lst):
        return [self.sched.hosts.find_by_name(name) for name in name_lst]

    def hostgroups_from_name_list(self, name_lst):
        return [self.sched.hostgroups.find_by_name(name) for name in name_lst]

    def test_simple_expand(self):
        name_lst = ['h_0_0', 'h_0_1', 'h_0_2']
        expected_members = self.hosts_from_name_list(name_lst)
        hg_0_0 = self.sched.hostgroups.find_by_name('hg_0_0')
        self.assertIsNotNone(hg_0_0)
        for host in hg_0_0.members:
            self.assertIn(host, expected_members)
            expected_members.remove(host)
        self.assertEqual([], expected_members)

    def test_expand_with_commas(self):
        name_lst = ['h_0_0', 'h_0_1', 'h_0_2']
        expected_members = self.hosts_from_name_list(name_lst)
        hg_1_0 = self.sched.hostgroups.find_by_name('hg_1_0')
        self.assertIsNotNone(hg_1_0)
        for host in hg_1_0.members:
            self.assertIn(host, expected_members)
            expected_members.remove(host)
        self.assertEqual([], expected_members)

    def test_nodeset_op(self):
        hostgroup = self.sched.hostgroups.find_by_name('hg_2_0')
        self.assertIsNotNone(hostgroup)
        name_lst = ['h_2_' + str(i) for i in range(60, 70)]
        expected_members = self.hosts_from_name_list(name_lst)
        for host in hostgroup.members:
            self.assertIn(host, expected_members)
            expected_members.remove(host)
        self.assertEqual([], expected_members)

    def test_expand_multi_line(self):
        name_lst = ['h_8_0', 'h_8_1', 'h_8_2']
        expected_members = self.hosts_from_name_list(name_lst)
        hg_8_0 = self.hostgroups_from_name_list(['hg_8_0'])[0]
        self.assertIsNotNone(hg_8_0)
        for host in hg_8_0.members:
            self.assertIn(host, expected_members)
            expected_members.remove(host)
        self.assertEqual([], expected_members)

if __name__ == '__main__':
    unittest.main()
