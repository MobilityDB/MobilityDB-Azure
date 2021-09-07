import os

import psycopg2
import subprocess


class CitusCluster:
    def __init__(self, coordinator_ip):
        self.POSTGREDB = os.environ['POSTGREDB']
        self.POSTGREUSER = os.environ['POSTGREUSER']
        self.POSTGREPASSWORD = os.environ['POSTGREPASSWORD']
        self.POSTGREPORT = os.environ['POSTGREPORT']
        self.COORDIP = coordinator_ip
        # Establish connection with the Citus Coordinator
        self.connection = psycopg2.connect(database=self.POSTGREDB, user=self.POSTGREUSER, password=self.POSTGREPASSWORD, host=self.COORDIP,
                               port=self.POSTGREPORT)
        print("Database opened successfully")

    def __del__(self):
        # Close the connection with the Citus Coordinator when the object is destroyed
        self.connection.close()
        print("Database closed successfully")
        
    def rebalance_table_shards(self):
            subprocess.run(["psql", "-U", self.POSTGREUSER , "-h", "localhost", "-p", self.POSTGREPORT, "-d", self.POSTGREDB, "-c", "SELECT rebalance_table_shards()"])
        # try:
        #     cur = self.connection.cursor()
        #
        #     # Rebalance table shards by running the corresponding query on the Coordinator
        #     cur.execute("SELECT rebalance_table_shards()")
        #
        #     # Commit the transaction
        #     self.connection.commit()
        #
        #     # Close the cursor
        #     cur.close()
        # except psycopg2.DatabaseError as e:
        #     print("Exception!!!")
        #     print(e)
        #     # Close the cursor
        #     cur.close()
        #     self.rebalance_table_shards()

    def delete_node(self, nodes_ip):
        cur = self.connection.cursor()

        for node_ip in nodes_ip:
            # Mark the worker node with node_ip to be deleted
            cur.execute("SELECT * FROM citus_set_node_property('%s', 5432, 'shouldhaveshards', false)" % node_ip)

        # Drain all the marked node at once
        cur.execute("SELECT * FROM rebalance_table_shards(drain_only := true)")

        # Remove the nodes from the Cluster
        for node_ip in nodes_ip:
            cur.execute("SELECT master_remove_node('%s', 5432)" % node_ip)

        # Commit the transaction
        self.connection.commit()

        # Close the cursor
        cur.close()

    def get_sessions_log_table(self, interval=3):
        cur = self.connection.cursor()

        # NOW row illustrates the AVERAGE number of active sessions the last "interval" minutes.
        # BEFORE row shows the same quantity between the last "interval" and "interval + 5" minutes.
        query = "\
                SELECT 'NOW' AS period, CEIL(AVG(users_number)) \
                FROM sessions_log \
                WHERE time > NOW() - interval '"+str(interval)+" minutes' \
                UNION \
                SELECT 'BEFORE' AS period, CEIL(AVG(users_number)) \
                FROM sessions_log \
                WHERE time > NOW() - interval '"+str(interval+5)+" minutes' AND time < NOW() - interval '"+str(interval)+" minutes'"

        # Execute the query
        cur.execute(query)

        # Fetch the results
        rows = cur.fetchall()

        # Close the cursor
        cur.close()

        return rows
