## Brodokk personal notes

> On things that need to be done before thinking doing any release

- [x] Fully connect the Discord auth with fastapi-users
- [x] Clean code the merge between discord and fastapi-users and commit
- [ ] Hide all private events unless
  - [x] They are connected
  - [x] The user have the role administrator
  - [x] The user have access to a community, in this case only the private event of this community are showed
- [ ] Verify the support of the JSON signal
- [ ] Seems like the Private communities and/or private events are not showed as tracked on the web page
- [ ] For better testing add a way for the admistrator to view the events as
  - [ ] A connected user and part of somes communities but not other
  - [ ] A connected user that is part of no communities
  - [ ] A non connected user
- [ ] Check the behavior for the API: text and json
- [ ] Go a check of all the TODO and FIXME