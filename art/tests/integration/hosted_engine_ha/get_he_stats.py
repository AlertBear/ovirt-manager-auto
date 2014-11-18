import ovirt_hosted_engine_ha.client.client as ha_cl  # pylint: disable=E0611

if __name__ == "__main__":
    he_client = ha_cl.HAClient()
    print he_client.get_all_stats()
