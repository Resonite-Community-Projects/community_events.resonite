## Brodokk personal notes

> On things that need to be done before thinking doing any release

- [ ] Add an admistrator role
- [ ] Hide all NSFW events to any users unless
  - [ ] They are connected
  - [ ] The configured discord role id in `private_role_id` match on of the use role
  - [ ] If no `private_role_id` the user is part of this discord server
  - [ ] The user have the role administrator
- [ ] For better testing add a way for the admistrator to view the events as
  - [ ] A connected user and part of somes communities but not other
  - [ ] A connected user that is part of no communities
  - [ ] A non connected user
- [ ] Check the behavior for the API: text and json
- [ ] Go a check of all the TODO and FIXME