import json
import os
import re

import attr


@attr.s(kw_only=True, frozen=True, slots=True)
class Moin2GitUser:
    moin_id: str = attr.ib()
    moin_name: str = attr.ib()
    email: str = attr.ib(default="user@example.org")

    @classmethod
    def load_user_from_file(cls, path, logger):
        data = open(path).read()
        moin_id = os.path.basename(path)
        user_dict = dict(re.findall(r"^([a-z_]+)=(.*)$", data, flags=re.MULTILINE))
        logger.debug(f"User data: {user_dict}")
        params = {"moin_id": moin_id, "moin_name": user_dict["name"]}
        if user_dict["email"] is not None and user_dict["email"] != "":
            params["email"] = user_dict["email"]
        user = cls(**params)
        return user


@attr.s(kw_only=True, frozen=True, slots=True)
class Moin2GitUserSet:
    id_map: dict = attr.ib(default={})
    name_map: dict = attr.ib(default={})

    @classmethod
    def create_from_users(cls, users, logger):
        id_map = {}
        name_map = {}
        for user in users:
            id_map[user.moin_id] = user
            name_map[user.moin_name] = user
        # make sure we have an anonymous entry for things we cannot put a user to
        if "anonymous" not in name_map:
            anonymous = Moin2GitUser(
                moin_id="0000000000.00.00000",
                moin_name="anonymous",
                email="anonymous@example.org",
            )
            id_map[anonymous.moin_id] = anonymous
            name_map[anonymous.moin_name] = anonymous
        # package all the users into a set
        logger.debug("Building user set object")
        return cls(id_map=id_map, name_map=name_map)

    @classmethod
    def load_users_from_wiki_data(cls, wiki_data_path, logger):
        users_dir = os.path.join(wiki_data_path, "user")
        logger.debug(f"Loading wiki users from {users_dir}")
        users = []
        for moin_id in os.listdir(users_dir):
            # check the moin id filename looks right
            if re.match(r"\d+\.\d+\.\d+$", moin_id):
                try:
                    logger.debug(f"Loading user id {moin_id}")
                    user = Moin2GitUser.load_user_from_file(
                        path=os.path.join(users_dir, moin_id),
                        logger=logger,
                    )
                    users.append(user)
                except OSError:
                    continue
        return cls.create_from_users(users=users, logger=logger)

    @classmethod
    def load_users_from_file(cls, path, logger):
        logger.debug(f"Loading wiki users from {path}")
        user_data_set = json.loads(open(path).read())
        users = []
        for entry in user_data_set:
            user = Moin2GitUser(**entry)
            users.append(user)
            logger.debug(f"Loaded user name {user.moin_name}")
        return cls.create_from_users(users=users, logger=logger)

    def save_users_to_file(self, path):
        user_data = []
        for user in self.name_map.values():
            user_data.append(attr.asdict(user))
        with open(path, "w") as f:
            json.dump(user_data, f, indent=2, sort_keys=True)

    def get_user_by_name(self, name):
        return self.name_map[name]

    def get_user_by_id(self, ident):
        return self.id_map[ident]

    def get_user_by_id_or_anonymous(self, ident):
        if ident is None or ident not in self.id_map:
            return self.get_user_by_name("anonymous")
        else:
            return self.get_user_by_id(ident)


# end
