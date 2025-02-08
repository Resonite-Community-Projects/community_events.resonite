## Brodokk personal notes

> On things that need to be done before thinking doing any release

- [x] Fully connect the Discord auth with fastapi-users
- [x] Clean code the merge between discord and fastapi-users and commit
- [ ] Hide all private events unless
  - [x] They are connected
  - [x] The user have the role administrator
  - [x] The user have access to a community, in this case only the private event of this community are showed
- [x] Verify the support of the JSON signal
- [x] Seems like the Private communities and/or private events are not showed as tracked on the web page
- [x] Put back the support of the rate-limit stuff
- [x] The stream signal collector seems to not work
- [x] Redo the doc on a website instead with mkdocs
- [x] For better testing add a way for the admistrator to view the events as
  - JUST think about a simple and nice way to do that in the code, i know i can just uncheck the option to go from super admin to simple user but this mean that i also to touch stuff in the database to remove some community to my user
  - Maybe add a bit of documentation on the subject? General documentation is needed anyway...
  - [x] A connected user and part of somes communities but not other
  - [x] A connected user that is part of no communities
  - [x] A non connected user
- [x] Make possible to start all the clients together (web and http api) on default port
  - [x] add an option to change host and port
  - [x] Update the documentation in consequence in "Developer Guide" > "Usage"
- [x] Check the behavior for the API: text and json
  - [x] Also update the documentation "Client Integration" at the same time
- [x] **FIX VERY BAD BUG** Look into why for whatever reason the cookies are not saved at all anymore
- [x] Fix the fact that the web interface and the API return only the event for Resonite and nothing else
  - [x] Save the location in tags for now, either vrchat or resonite
  - [x] Only show the events for resonite in the webinterface
  - [x] Only show the events for resonite in the API
- [ ] Remove useless tags from the web client as: "public", "resonite"
- [ ] Go a check of all the TODO and FIXME
- [ ] Set up the new stack for production (and preproduction) with docker container and such
  - [ ] Update the documentation in "Developer Guide" > "Server Installation"
  - Keep in mind to ease the developement process so we should still be able to use sqlite locally while use a postgresql instance while on the production stack
- [ ] Set up the deployment in preproduction (beta.resonite-communities.com) as well as the documentation (docs.beta.resonite-communities.com)
- [ ] Update the documentation to explain more the architecture part as well as the usage guide
  - [ ] Update the url documentation to `docs.beta.resonite-communities.com` in the README