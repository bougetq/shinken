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

    def test_simple_expand(self):
        expected_members = ['h_0_0', 'h_0_1', 'h_0_2', 'h_0_3', 'h_0_4']
        expected_members = [self.sched.hosts.find_by_name(name)\
                            for name in expected_members]
        hg_0_0 = self.sched.hostgroups.find_by_name('hg_0_0')
        self.assertIsNotNone(hg_0_0)
        for host in hg_0_0.members:
            self.assertTrue(host in expected_members,
                            'unexpected member in hg_0_0')
            expected_members.remove(host)
        self.assertEqual([], expected_members, 'missing members in hg_0_0')

    def test_nodeset_op(self):
        hostgroup = self.sched.hostgroups.find_by_name('hg_8_0')
        self.assertIsNotNone(hostgroup, 'missing hostgroup hg_8_0')
        expected_members = [self.sched.hosts.find_by_name('h_8_' + str(i))\
                            for i in range(60, 70)]
        for member in hostgroup.members:
            self.assertTrue(member in expected_members,\
                            'unexpected member %s for hostgroup hg_8_0' %\
                            member.host_name)
            expected_members.remove(member)

        self.assertEqual([], expected_members,\
                         'missing member(s) for hostgroup hg_8_0')


if __name__ == '__main__':
    unittest.main()
