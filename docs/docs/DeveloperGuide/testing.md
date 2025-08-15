---
title: Testing
prev: DeveloperGuide/migrations.md
---

For now their is no unit test but this is the thing to keep in mind when doing functional testing.

## Preview private events based on different user permissions

This is really important that users, connected or no, doesn't have access to certain private events in one context: Adult events.

To avoid this here is different tests.

### Test as anonymous user

> For user who are not part of private community or just don't want to connect.

Just don't connect at all with Discord. You should not see any private events.

### Test as administrator

> When developing your should be a superuser.

Connect to Discord and you should see all events, public and private. In the database, the column `is_superuser` of the table `user` should be `True` for the user you are currently connected with.

### Test as a non administrator

> Usual normal user who want to see the events for the private community they are part of.

Connect to Discord and you should see all the public events and the private events that your user have access to. In the database, the column `is_superuser` of the table `user` should be `False`.

You can simulate the fact the user is not part of some communities by editing the correct row in the `discord_account` table. Remove some id in the `user_communities` **after** you are logged in with your Discord user into the app. Keep in mind logging out and relogin after will reset the column so you need to redo this again. (See the section about configuring the Discord bot and it's callback.)
