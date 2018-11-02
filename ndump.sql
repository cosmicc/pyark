PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE instances(name TEXT, lastrestart TEXT, lastdinowipe TEXT, needsrestart BOOL, lastvote TEXT, restartreason TEXT, cfgver TEXT, restartcountdown INTEGER, arkserverkey TEXT, isup INTEGER, islistening INTEGER, isrunning INTEGER, uptimestamp TEXT, actmem TEXT, totmem TEXT, steamlink TEXT, arkserverslink TEXT, battlemetricslink TEXT, arkversion TEXT, uptime INTEGER, rank INTEGER, score INTEGER, votes INTEGER, hostname TEXT, inevent INTEGER);
INSERT INTO instances VALUES('ragnarok','1541104451.4292417','1541161940','False','1541161940','[RareSightings] mod update','31',30,'6TO5zDDQk9uiywI9aJp9IYjmZmNHZn98DzE',1,1,1,'1541189461.22715','9.01','10.35','steam://connect/173.15.226.42:47016','https://ark-servers.net/server/147631','https://www.battlemetrics.com/servers/ark/2526676','284.104',100,966,2,0,'Galaxy Cluster Ultimate Extinction Core Ragnarok - (v284.104)',0);
INSERT INTO instances VALUES('volcano','1541102511.7617319','1541117556.9154189','False','1540857964.66911','[RareSightings] mod update','31',30,'tcomXek4ZwOobPVsqaFKy2eeL4vS1xvUt',1,1,1,'1541189468.84396','8.39','9.65','steam://connect/173.15.226.42:47018','https://ark-servers.net/server/150747','https://www.battlemetrics.com/servers/ark/2636402','284.104',99,1332,2,0,'Galaxy Cluster Ultimate Extinction Core Volcano - (v284.104)',0);
INSERT INTO instances VALUES('island','1541102544.0663385','1541115911.868049','False','1540856314.0684','[RareSightings] mod update','31',30,'xcmOgkKFziAjDNhSAdTIH0w6fBMjOo50dpk',1,1,1,'1541189470.94183','6.79','9.89','steam://connect/173.15.226.42:47020','https://ark-servers.net/server/150746','https://www.battlemetrics.com/servers/ark/2637018','284.104',99,1331,2,0,'Galaxy Cluster Ultimate Extinction Core Island - (v284.104)',0);
CREATE TABLE players(steamid INTEGER, playername TEXT, lastseen REAL, server TEXT, playedtime REAL, rewardpoints INTEGER, firstseen REAL, connects INTEGER, discordid TEXT, banned TEXT, totalauctions INTEGER, itemauctions INTEGER, dinoauctions INTEGER, restartbit INTEGER, primordialbit INTEGER, homeserver TEXT, transferpoints INTEGER, lastpointtimestamp TEXT, lottowins INTEGER, lotterywinnings INTEGER, email TEXT, password TEXT, apikey TEXT);
INSERT INTO players VALUES(76561198177173167,'weiser',1539370841.9999999999,'ragnarok',746999.93799999996552,3296,1537205920.7565701008,45,'weiser#3768','',0,0,0,1,0,'ragnarok',0,'1538317751.991779',1,240,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198097858297,'the hound',1537222830.9999999999,'ragnarok',249041.67199999999139,721,1537205920.7565701008,2,'','',NULL,NULL,NULL,1,0,'ragnarok',0,'1538186193.20081',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198136444876,'shepard',1537316795.0,'ragnarok',14495.499999999999999,307,1537205920.7565701008,2,'','',NULL,NULL,NULL,1,0,'ragnarok',0,'1538186193.20081',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198078911535,'the chin',1537222637.0,'ragnarok',316799.93800000002374,4092,1537205920.7565701008,2,'','',NULL,NULL,NULL,1,0,'ragnarok',0,'1538186193.20081',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198033437177,'sheriffen',1541022252.9999999999,'ragnarok',1139399.875,6484,1537205920.7565701008,57,'sheriffen#8983','',0,0,0,0,1,'ragnarok',0,'1538186193.20081',1,800,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198315422761,'dude',1540665503.9999999999,'ragnarok',241199.99999999999999,852,1537205920.7565701008,15,'','',0,0,0,1,0,'ragnarok',0,'1538186193.20081',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198305978693,'shark',1539470849.0,'ragnarok',73840.906000000002679,875,1537205920.7565701008,2,'','',0,0,0,1,0,'ragnarok',0,'1538186193.20081',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561197973691379,'addrianna',1541030842.0,'island',553740.0,3384,1537205920.7565701008,45,'addrianna#4562','',0,0,0,1,0,'island',0,'1541029589.6218796',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198319536877,'thom fulari',1541171067.5831134318,'ragnarok',449999.96899999998275,1994,1537205920.7565701008,92,'','',0,0,0,1,0,'ragnarok',0,'1538186193.20081',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198388849736,'rykker',1540866562.0,'ragnarok',453599.90600000001724,5407,1537205920.7565701008,56,'rykker#7393','',0,0,0,0,0,'ragnarok',0,'1539654224.3787873',0,0,NULL,NULL,'uKG1Wy9ipm0eZI4f7SdhBIScJ1OaWdJ4');
INSERT INTO players VALUES(76561198027678472,'skeet',1541169587.4938046932,'ragnarok',258948.29699999999139,3286,1537205920.7565701008,16,'skeet#1292','',0,0,0,1,0,'ragnarok',0,'1538186193.20081',1,240,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198166052963,'zauron',1540414958.9999999999,'volcano',638015.37499999999999,7645,1537205920.7565701008,80,'zauron#4247','',0,0,0,1,0,'volcano',0,'1538977806.3590035',2,350,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198326525737,'crazydogg',1537197512.9999999999,'island',28687.006000000001221,499,1537205920.7565701008,1,'','',NULL,NULL,NULL,1,0,'island',0,'1538186193.20081',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198059198389,'dazimek',1537315447.9999999999,'ragnarok',16586.434000000001105,64,1537235457.3236598968,3,'','',NULL,NULL,NULL,1,0,'ragnarok',0,'1538186193.20081',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198028548947,'karma',1537731883.0,'ragnarok',144000.0,471,1537249560.6013300418,13,'','',NULL,NULL,NULL,1,0,'ragnarok',0,'1538186193.20081',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198187923238,'sushi',1537731623.0,'ragnarok',144000.0,421,1537249237.7624800205,12,'','',NULL,NULL,NULL,1,0,'ragnarok',0,'1538186193.20081',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198408657294,'admin',1541043773.9999999999,'ragnarok',3925.2860000000000582,93640,1537300423.9999999999,103,'galaxy cluster#2744','',0,0,0,1,0,'ragnarok',0,'1540780302.3337183',1,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198085599232,'get trippy',1537314544.9999999999,'ragnarok',500.46800000000001775,50,1537313517.2167201042,1,'','',NULL,NULL,NULL,1,0,'ragnarok',0,'1538186193.20081',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198118212362,'spiffy',1539995218.0,'island',178457.25,3038,1537337107.7372899055,33,'spiffiestbook07#0405','',0,0,0,1,0,'island',0,'1538269689.4150174',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198332748953,'eclipse',1537388607.0,'island',2947.2029999999999744,50,1537385263.3765499591,1,'','',NULL,NULL,NULL,1,0,'island',0,'1538186193.20081',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198056834745,'wheats',1539528136.9999999999,'volcano',397155.78100000001724,595,1537407777.8572199344,24,'wheats#8243','',0,0,0,1,0,'ragnarok',75,'1539528162.9265928',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198061944366,'elsynia',1540351132.9999999999,'ragnarok',508201.56199999997623,805,1537546754.3991498946,28,'elsynia#7739','',0,0,0,1,0,'ragnarok',0,'1540349498.1075516',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198070644692,'markimus',1541048031.0,'ragnarok',987798.81200000003447,17598,1537322969.0,79,'markimus#7102','',0,0,0,0,1,'ragnarok',0,'1539016420.0092087',2,435,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198045395474,'bartimusprime',1538820416.9999999999,'ragnarok',417599.87499999999998,1358,1537575713.293970108,30,'bartimusprime#1360','',1,1,0,1,0,'ragnarok',0,'1538808764.8748548',1,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198201993632,'jjonnesyy',1538283916.9999999999,'island',210599.96900000001187,54,1537590231.9999999999,10,'jjonesyy#3190','',0,0,0,1,0,'island',0,'1538190553.2909756',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198010354323,'saber',1538291023.9999999999,'ragnarok',47266.828000000001338,435,1537669814.2608299255,12,'extremesaber#4726','',0,0,0,1,0,'island',200,'1538290140.2610745',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198065314938,'venka',1538891478.9999999999,'ragnarok',261000.03099999998811,2510,1537670891.4047501087,46,'kibbles#3627','',0,0,0,1,0,'ragnarok',0,'1538455304.0036974',1,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198447510706,'ion',1537729069.9999999999,'ragnarok',4024.760999999999967,100,1537725970.1102499961,1,'','',NULL,NULL,NULL,1,0,'ragnarok',0,'1538186193.20081',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198174619015,'buttercorn',1538690047.9999999999,'ragnarok',52199.991999999998371,950,1537728279.4234800339,11,'','',0,0,0,1,0,'ragnarok',0,'1538186193.20081',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198193093534,'doomfire103',1538866123.0,'ragnarok',10107.409999999999854,85,1537741699.4159998893,9,'♥⭕🏹oryx(づ^ö^)づ🏹⭕♥#2853','',0,0,0,1,0,'island',150,'1538866147.73465',1,8,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198096941282,'syn',1537755097.9999999999,'ragnarok',554.07600000000002183,50,1537751058.1937100887,1,'','',NULL,NULL,NULL,1,0,'ragnarok',0,'1538186193.20081',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561197970976201,'snuffy',1540286058.0,'ragnarok',43199.987999999997553,721,1537788114.594700098,11,'snuffy#8617','',0,0,0,1,0,'ragnarok',0,'1538186193.20081',1,400,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198103669462,'asperum',1540147869.0,'ragnarok',9163.1800000000002909,82,1537858176.2176098823,2,'','',0,0,0,1,0,'ragnarok',0,'1538186193.20081',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198258322345,'lycanml',1538057245.9999999999,'island',525.24099999999998545,50,1538056371.6068100929,1,'','',0,0,0,0,0,'island',0,'1538186193.20081',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198114814563,'nolun',1538179019.0,'volcano',3599.9999999999999999,100,1538123348.7726099491,2,'','',0,0,0,0,0,'volcano',0,'1538186193.20081',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198012621627,'respawn',1539206292.0,'volcano',289800.03100000001722,1144,1538144032.2993700504,22,'destini#3410','',0,0,0,0,0,'volcano',0,'1538766888.7330956',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198349014755,'tin',1539230146.0,'volcano',298799.99999999999999,4319,1538144508.5241100788,21,'tindin#6907','',0,0,0,0,0,'volcano',0,'1538583291.4554205',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198032063261,'haus',1540584460.9999999999,'ragnarok',196200.03099999998812,4550,1538188150.4862399101,42,'','',0,0,0,0,0,'ragnarok',0,'1540399417.552215',2,630,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198032068901,'temp',1540619834.9999999999,'ragnarok',777782.00000000000001,6993,1538193111.236759901,73,'zhayl#6647','',0,0,0,0,0,'ragnarok',0,'1540574841.9917514',1,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198191351331,'damion',1538209381.9999999999,'island',2240.0129999999999199,50,1538206707.9554500579,1,'','',0,0,0,0,0,'island',0,'1538206707.95545',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198096395894,'jane',1538521112.0,'ragnarok',14400.0,250,1538211610.4134900569,3,'','',0,0,0,0,0,'ragnarok',0,'1538211610.41349',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198011265490,'nosferatu',1538787153.9999999999,'volcano',187402.875,1254,1538265060.085750103,12,'','',0,0,0,0,0,'ragnarok',0,'1538722379.6009839',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198293381146,'draxx',1538338170.9999999999,'ragnarok',157.01800000000000067,50,1538337817.174380064,1,'','',0,0,0,0,0,'ragnarok',0,'1538337817.17438',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198214279745,'critkill',1538358186.9999999999,'volcano',1799.9999999999999999,75,1538355733.4983799457,1,'','',0,0,0,0,0,'volcano',0,'1538355733.49838',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198009383034,'bigb',1541108305.0,'ragnarok',94299.741999999998369,1350,1538507838.9806399345,25,'','',0,0,0,0,0,'ragnarok',0,'1538507838.98064',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561197998650506,'vangarrot',1539035669.9999999999,'ragnarok',90000.008000000001626,1300,1538621707.4450199603,8,'','',0,0,0,0,0,'ragnarok',0,'1538621707.44502',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198169185429,'anntez',1538650080.9999999999,'ragnarok',273.40399999999999635,50,1538649137.7048900127,2,'','',0,0,0,0,0,'ragnarok',0,'1538649137.70489',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198038721303,'xeno',1539142841.0,'volcano',102599.98399999999674,465,1538690703.0747098922,10,'trippy993#9936','',0,0,0,0,0,'volcano',0,'1538690703.07471',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198374860090,'kayla',1539142549.9999999999,'volcano',83475.898000000001049,830,1538692947.3341100215,7,'kaylamari#4410','',0,0,0,0,0,'volcano',0,'1538692947.33411',1,160,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198371096932,'zombie',1538698074.9999999999,'island',93.721999999999994201,50,1538696661.8721098899,1,'','',0,0,0,0,0,'island',0,'1538696661.87211',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198419158273,'mondo',1541125694.9999999999,'ragnarok',459000.00000000000001,6170,1538856941.3341999053,57,'mondochop#6916','',0,0,0,0,0,'ragnarok',0,'1540584995.2130399',3,1320,NULL,NULL,NULL);
INSERT INTO players VALUES(76561197969170395,'disturbed',1538926541.0,'ragnarok',344.1449999999999818,50,1538924827.5397799014,1,'','',0,0,0,0,0,'ragnarok',0,'1538924827.53978',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198087385691,'humano',1538980024.9999999999,'ragnarok',3599.9999999999999999,55,1538975720.5055100917,1,'','',0,0,0,0,0,'ragnarok',0,'1538975720.50551',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198000597345,'iparadox',1539033962.9999999999,'volcano',356.04399999999998271,50,1539029123.7962799072,2,'','',0,0,0,0,0,'volcano',0,'1539029123.79628',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198799305966,'wolf',1539044530.0,'ragnarok',373.03300000000001546,50,1539037798.5020899773,2,'','',0,0,0,0,0,'ragnarok',0,'1539037798.50209',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198089548860,'eleagle12',1540248655.0,'ragnarok',212855.92199999999137,355,1539040022.1427400111,31,'eleagle12#3628','',0,0,0,0,0,'ragnarok',0,'1540247667.7562351',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198122753389,'bubba',1539047244.0,'ragnarok',2814.1120000000000799,75,1539044174.1673300266,1,'','',0,0,0,0,0,'ragnarok',0,'1539044174.16733',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198007739284,'smegma',1539869552.0,'volcano',4006.7609999999999671,65,1539049449.5760900974,3,'','',0,0,0,0,0,'volcano',0,'1539049449.57609',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198138039059,'kyle katarn',1541163288.6025178432,'ragnarok',478800.03100000001724,608,1539219486.950799942,60,'soldierkatarn#2346','',0,0,0,0,0,'ragnarok',0,'1539401798.60239',1,390,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198043565764,'sam',1539463891.9999999999,'ragnarok',17999.999999999999999,200,1539287318.7379500865,5,'spacestar#3807','',0,0,0,0,0,'ragnarok',0,'1539287318.73795',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198176898177,'fadingmemories',1539908583.9999999999,'ragnarok',14400.0,250,1539292350.1367099285,3,'','',0,0,0,0,0,'ragnarok',0,'1539292350.13671',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198117041339,'karmic',1539357631.0,'island',7199.9999999999999998,150,1539321417.8847100734,3,'karmico#0497','',0,0,0,0,0,'island',0,'1539321417.88471',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198072981496,'sans the skeleton.',1539329710.9999999999,'ragnarok',1799.9999999999999999,75,1539326921.4557299614,1,'','',0,0,0,0,0,'ragnarok',0,'1539326921.45573',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198423807679,'killing',1539381725.0,'island',5400.0,25,1539376275.9341900348,1,'','',0,0,0,0,0,'island',0,'1539376275.93419',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198126963396,'munchie',1539446869.9999999999,'island',1799.9999999999999999,75,1539443987.8095800876,1,'','',0,0,0,0,0,'island',0,'1539443987.80958',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198022368672,'roman',1539499707.0,'ragnarok',250.55899999999999749,149,1539499499.1848199367,1,'','',0,0,0,0,0,'ragnarok',0,'1539499499.18482',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198050723205,'rakkash',1539634528.0,'ragnarok',14400.0,250,1539571049.0934801102,3,'','',0,0,0,0,0,'ragnarok',0,'1539571049.09348',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198012710782,'sumax',1541189529.6039288044,'ragnarok',626399.99999999999998,4860,1539573866.1569800376,53,'sumax#0721','',0,0,0,0,1,'ragnarok',0,'1540995071.8415854',3,1950,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198340898509,'failkor',1540091424.9999999999,'volcano',716.44000000000005456,50,1539648134.0917699336,2,'','',0,0,0,0,0,'ragnarok',50,'1540090298.5129411',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198318111699,'theresa',1539726972.0,'volcano',871.34699999999997996,50,1539726891.3224599361,1,'','',0,0,0,0,0,'volcano',0,'1539726891.32246',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198038808754,'thrall',1540419259.0,'volcano',181649.37499999999999,1340,1539728165.7059600353,28,'thrall#2987','',0,0,0,0,0,'ragnarok',100,'1540419055.22697',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198079263495,'maniac',1540139391.9999999999,'volcano',55799.999999999999999,790,1539735229.4001400469,14,'','',0,0,0,0,0,'ragnarok',50,'1540138470.4172337',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198105867840,'inale',1539805978.0,'island',744.67399999999997818,50,1539805626.454390049,1,'','',0,0,0,0,0,'island',0,'1539805626.45439',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198100187730,'maliblues',1539982587.9999999999,'island',607.70799999999996999,50,1539979182.2047400474,1,'','',0,0,0,0,0,'island',0,'1539979182.20474',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198073613364,'peytowhin',1540136945.9999999999,'ragnarok',52199.999999999999998,775,1540059569.285779953,3,'','',0,0,0,0,0,'ragnarok',0,'1540059569.28578',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198048649293,'starfort',1540594466.9999999999,'island',23399.999999999999999,225,1540066850.9283299445,7,'','',0,0,0,0,0,'island',0,'1540066850.92833',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198129131705,'scarlet',1540501799.0,'island',16199.999999999999999,125,1540073562.7636399268,4,'','',0,0,0,0,0,'island',0,'1540073562.76364',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198032302602,'osbourne',1540085158.9999999999,'ragnarok',7644.8400000000001457,150,1540076133.3501598835,1,'','',0,0,0,0,0,'ragnarok',0,'1540076133.35016',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198068871201,'az',1541145730.3475461006,'ragnarok',214199.99999999999999,1133,1540116117.251420021,16,'','',0,0,0,0,0,'ragnarok',0,'1541140156',1,750,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198130061722,'r35pect',1541114247.0,'ragnarok',93599.999999999999996,1385,1540237815.610179901,16,'','',0,0,0,0,0,'ragnarok',0,'1540237815.61018',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198087757895,'fieryx',1541104174.9999999999,'ragnarok',73800.000000000000001,1317,1540239208.7579200268,19,'','',0,0,0,0,0,'ragnarok',0,'1540239208.75792',0,0,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198014729954,'keblin',1540399924.0,'ragnarok',1799.9999999999999999,75,1540398079.38793993,1,'','',0,0,0,0,0,'ragnarok',0,'1540398079.38794',0,NULL,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198037030122,'docterapple',1541189529.614477396,'ragnarok',263117.93800000002373,3471,1540455810.6201701164,28,'','',0,0,0,0,0,'ragnarok',0,'1540455810.62017',0,NULL,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198037509568,'kryptiqghost',1540541029.0,'ragnarok',1799.9999999999999999,75,1540538871.1145200729,1,'','',0,0,0,0,0,'ragnarok',0,'1540538871.11452',0,NULL,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198220618449,'nick',1540688513.9999999999,'ragnarok',3201.7040000000001782,335,1540608737.5544738769,3,'','',0,0,0,0,0,'island',1157,'1540666007.707414',0,NULL,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198184903759,'has',1540689366.0,'ragnarok',4110.699999999999818,150,1540662986.7228925227,2,'','',0,0,0,0,0,'ragnarok',0,'1540662986.72289',0,NULL,NULL,NULL,NULL);
INSERT INTO players VALUES(76561197970406025,'gorechild',1540754355.0,'island',3652.1529999999997925,150,1540724463.022119522,2,'','',0,0,0,0,0,'island',0,'1540724463.02212',0,NULL,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198016874433,'tr0jan',1540754376.0,'island',305.03199999999998225,50,1540753945.6974532603,1,'','',0,0,0,0,0,'island',0,'1540753945.69745',0,NULL,NULL,NULL,NULL);
INSERT INTO players VALUES(76561197973494656,'vultrax',1540810238.9999999999,'ragnarok',5400.0,180,1540804354.8517727851,1,'','',0,0,0,0,0,'ragnarok',0,'1540804354.85177',0,NULL,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198072184298,'jennburger',1541035893.0,'ragnarok',68983.789000000004308,1284,1540861872.6687309741,10,'jennburger#4878','',0,0,0,0,0,'ragnarok',0,'1540861872.66873',0,NULL,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198048673212,'aj',1541053432.0,'ragnarok',4200.5540000000000872,200,1540996952.5801651478,4,'','',0,0,0,0,0,'ragnarok',0,'1541004042.4988296',0,NULL,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198042200259,'syndrome',1541092241.9999999999,'ragnarok',2354.8510000000001127,100,1541020196.9465551376,2,'','',0,0,0,0,0,'ragnarok',0,'1541020196.9465551',0,NULL,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198053758403,'nobo',1541047371.0,'ragnarok',14400.0,500,1541020321.3740425109,3,'','',0,0,0,0,0,'ragnarok',0,'1541020321.3740425',0,NULL,NULL,NULL,NULL);
INSERT INTO players VALUES(76561198207611892,'trav the mighty',1541188728.7493283748,'ragnarok',240.14599999999998657,50,1541188098.0,1,'','',0,0,0,0,0,'ragnarok',0,'1541188098',0,NULL,NULL,NULL,NULL);
CREATE TABLE discordnames (discordname TEXT);
INSERT INTO discordnames VALUES('Rykker#7393');
INSERT INTO discordnames VALUES('Galaxy Cluster#2744');
INSERT INTO discordnames VALUES('Sheriffen#8983');
INSERT INTO discordnames VALUES('Markimus#7102');
INSERT INTO discordnames VALUES('Addrianna#4562');
INSERT INTO discordnames VALUES('Wheats#8243');
INSERT INTO discordnames VALUES('Zauron#4247');
INSERT INTO discordnames VALUES('Weiser#3768');
INSERT INTO discordnames VALUES('Elsynia#7739');
INSERT INTO discordnames VALUES('Galaxy Cluster#7499');
INSERT INTO discordnames VALUES('BartimusPrime#1360');
INSERT INTO discordnames VALUES('server-notifications#0000');
INSERT INTO discordnames VALUES('Jjonesyy#3190');
INSERT INTO discordnames VALUES('AKsnow#7107');
INSERT INTO discordnames VALUES('Mantuh#7840');
INSERT INTO discordnames VALUES('Karma#0117');
INSERT INTO discordnames VALUES('Kibbles#3627');
INSERT INTO discordnames VALUES('ExtremeSaber#4726');
INSERT INTO discordnames VALUES('SlayerEmpyreus#4431');
INSERT INTO discordnames VALUES('Spiffiestbook07#0405');
INSERT INTO discordnames VALUES('skeet#1292');
INSERT INTO discordnames VALUES('jjstar511#8589');
INSERT INTO discordnames VALUES('Snuffy#8617');
INSERT INTO discordnames VALUES('Asperum#3498');
INSERT INTO discordnames VALUES('Sam (Samayl)#4568');
INSERT INTO discordnames VALUES('Slywolf117#7892');
INSERT INTO discordnames VALUES('Destini#3410');
INSERT INTO discordnames VALUES('-EagleWolf-#5150');
INSERT INTO discordnames VALUES('Zhayl#6647');
INSERT INTO discordnames VALUES('Respawn#7501');
INSERT INTO discordnames VALUES('Tindin#6907');
INSERT INTO discordnames VALUES('Nosferatu Zodd#9045');
INSERT INTO discordnames VALUES('Nosferatu#7981');
INSERT INTO discordnames VALUES('♥⭕🏹Oryx(づ^ö^)づ🏹⭕♥#2853');
INSERT INTO discordnames VALUES('DemiVFX#6969');
INSERT INTO discordnames VALUES('trippy993#9936');
INSERT INTO discordnames VALUES('Kaylamari#4410');
INSERT INTO discordnames VALUES('Cabin#5998');
INSERT INTO discordnames VALUES('Disturbed#1703');
INSERT INTO discordnames VALUES('DJ_hellscythe#0477');
INSERT INTO discordnames VALUES('eleagle12#3628');
INSERT INTO discordnames VALUES('Soldierkatarn#2346');
INSERT INTO discordnames VALUES('🌕FadingMemories🐺#3850');
INSERT INTO discordnames VALUES('Spacestar#3807');
INSERT INTO discordnames VALUES('Mondochop#6916');
INSERT INTO discordnames VALUES('KarmiCo#0497');
INSERT INTO discordnames VALUES('PurpleWar-Stonebraker#8475');
INSERT INTO discordnames VALUES('Kalmar#2085');
INSERT INTO discordnames VALUES('Sumax#0721');
INSERT INTO discordnames VALUES('eopq423#4379');
INSERT INTO discordnames VALUES('Thrall#2987');
INSERT INTO discordnames VALUES('Ryuufire26#9260');
INSERT INTO discordnames VALUES('Jennburger#4878');
INSERT INTO discordnames VALUES('Soul#1947');
INSERT INTO discordnames VALUES('Haus#9655');
INSERT INTO discordnames VALUES('Haus#4704');
INSERT INTO discordnames VALUES('booty#0641');
INSERT INTO discordnames VALUES('maliblues#8209');
INSERT INTO discordnames VALUES('abysshunter25#2281');
INSERT INTO discordnames VALUES('abysshunter25#5783');
INSERT INTO discordnames VALUES('WitchyCat#6750');
INSERT INTO discordnames VALUES('i_has#0357');
INSERT INTO discordnames VALUES('Zinbar#7585');
INSERT INTO discordnames VALUES('ggina888#3780');
INSERT INTO discordnames VALUES('Radu#1749');
INSERT INTO discordnames VALUES('Shizuko#7498');
INSERT INTO discordnames VALUES('InTheory#5373');
INSERT INTO discordnames VALUES('docterapple#7421');
CREATE TABLE kicklist (instance TEXT, steamid TEXT);
CREATE TABLE linkrequests (steamid TEXT, name TEXT, reqcode TEXT);
INSERT INTO linkrequests VALUES('76561198011265490','nosferatu','1584');
INSERT INTO linkrequests VALUES('76561198079263495','maniac','5364');
INSERT INTO linkrequests VALUES('76561198220618449','nick','8465');
CREATE TABLE chatbuffer (server TEXT, name TEXT, message TEXT, timestamp TEXT);
CREATE TABLE banlist (steamid TEXT);
CREATE TABLE auctions (steamid TEXT, date TEXT, Type TEXT, name TEXT, sellingclass TEXT, quantity TEXT, askingclass TEXT, askingamount TEXT, tamedname TEXT, baselevel INTEGER, extrlevel INTEGER, level INTEGER, gender TEXT, quality INTEGER, rating REAL, armor REAL, durability REAL, damage REAL, blueprint TEXT);
CREATE TABLE globalbuffer (id INTEGER PRIMARY KEY AUTOINCREMENT, server TEXT, name TEXT, message TEXT, timestamp TEXT);
CREATE TABLE lotteryinfo (id INTEGER PRIMARY KEY AUTOINCREMENT, type INTEGER, payoutitem TEXT, timestamp TEXT, buyinpoints INTEGER, lengthdays INTEGER, players INTEGER, winner TEXT, announced INTEGER);
INSERT INTO lotteryinfo VALUES(10,'points','8','1538280212.27791',1,1,6,'doomfire103',1);
INSERT INTO lotteryinfo VALUES(11,'points','240','1538285490.71734',20,14,10,'skeet',1);
INSERT INTO lotteryinfo VALUES(15,'points','35','1538786889.11335',5,1,5,'markimus',1);
INSERT INTO lotteryinfo VALUES(16,'item','20x biotoxin','1538801641.90966',1,1,3,'bartimusprime',1);
INSERT INTO lotteryinfo VALUES(17,'points','50','1538847025.7089',10,1,3,'zauron',1);
INSERT INTO lotteryinfo VALUES(18,'points','400','1538860583.11985',50,2,6,'markimus',1);
INSERT INTO lotteryinfo VALUES(19,'points','200','1538962910.47042',50,1,2,'None',1);
INSERT INTO lotteryinfo VALUES(20,'points','300','1538973891.38065',50,18,4,'zauron',1);
INSERT INTO lotteryinfo VALUES(21,'points','160','1539045616.20312',20,10,6,'kayla',1);
INSERT INTO lotteryinfo VALUES(22,'points','350','1539094243.04198',50,9,5,'haus',1);
INSERT INTO lotteryinfo VALUES(23,'points','200','1539132481.11766',50,9,0,'None',1);
INSERT INTO lotteryinfo VALUES(24,'points','250','1539277851.37251',50,8,1,'None',1);
INSERT INTO lotteryinfo VALUES(25,'points','240','1539311086.67714',20,22,8,'weiser',1);
INSERT INTO lotteryinfo VALUES(26,'points','250','1539402108.58021',50,13,1,'None',1);
INSERT INTO lotteryinfo VALUES(27,'points','400','1539469009.05523',50,24,4,'snuffy',1);
INSERT INTO lotteryinfo VALUES(28,'points','350','1539891653.39708',50,6,3,'sumax',1);
INSERT INTO lotteryinfo VALUES(29,'points','280','1539914896.23608',20,20,4,'haus',1);
INSERT INTO lotteryinfo VALUES(30,'points','480','1539996911.91222',30,14,6,'mondo',1);
INSERT INTO lotteryinfo VALUES(31,'points','240','1540070425.44175',20,6,2,'None',1);
INSERT INTO lotteryinfo VALUES(32,'points','390','1540150371.28882',30,7,3,'mondo',1);
INSERT INTO lotteryinfo VALUES(33,'points','750','1540178540.05349',50,21,5,'az',1);
INSERT INTO lotteryinfo VALUES(34,'points','390','1540313774.88114',30,8,3,'kyle katarn',1);
INSERT INTO lotteryinfo VALUES(35,'points','850','1540357274.52678',50,43,7,'sumax',1);
INSERT INTO lotteryinfo VALUES(36,'points','800','1540564690.44571',50,52,6,'sheriffen',1);
INSERT INTO lotteryinfo VALUES(38,'points','450','1540785835.44331',30,67,5,'mondo',1);
INSERT INTO lotteryinfo VALUES(39,'points','750','1541036257.27529',50,5,5,'sumax',1);
INSERT INTO lotteryinfo VALUES(40,'points','520','1541135482.44623',40,48,3,'Incomplete',1);
CREATE TABLE lotteryplayers (steamid TEXT, playername TEXT, timestamp TEXT, paid INTEGER);
INSERT INTO lotteryplayers VALUES('76561198027678472','skeet','1541168257',0);
INSERT INTO lotteryplayers VALUES('76561198319536877','thom fulari','1541169312',0);
INSERT INTO lotteryplayers VALUES('76561198012710782','sumax','1541172859',0);
CREATE TABLE lotterydeposits (steamid TEXT, playername TEXT, timestamp TEXT, points INTEGER, givetake INTEGER);
INSERT INTO lotterydeposits VALUES('76561197998650506','vangarrot','1539038714.13603',50,0);
INSERT INTO lotterydeposits VALUES('76561198122753389','bubba','1539081630.84996',20,0);
INSERT INTO lotterydeposits VALUES('76561198177173167','weiser','1539390304.08286',240,1);
INSERT INTO lotterydeposits VALUES('76561198038808754','thrall','1540512117.38252',50,0);
INSERT INTO lotterydeposits VALUES('76561198032068901','temp','1540751905.47926',50,0);
CREATE TABLE general (cfgver TEXT, announce TEXT);
INSERT INTO general VALUES('31',NULL);
CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, completed INTEGER, starttime REAL, endtime REAL, title TEXT, description TEXT, cfgfilesuffix TEXT);
INSERT INTO events VALUES(1,1,1540551600.0,1541030399.9999999999,'Halloween Weekend','2X Xp, 2X Reward Points, Transmitter Coords','halloween');
INSERT INTO events VALUES(2,1,1541030399.9999999999,1541069999.9999999999,'Hell On Ark','Dinos Have Risen From Hell. Permanent Night.','hellonark');
CREATE TABLE players2(steamid INTEGER, playername TEXT, lastseen INTEGER, server TEXT, playedtime INTEGER, rewardpoints INTEGER, firstseen INTEGER, connects INTEGER, discordid TEXT, banned TEXT, totalauctions INTEGER, itemauctions INTEGER, dinoauctions INTEGER, restartbit INTEGER, primordialbit INTEGER, homeserver TEXT, transferpoints INTEGER, lastpointtimestamp TEXT, lottowins INTEGER, lotterywinnings INTEGER, email TEXT, password TEXT, apikey TEXT);
INSERT INTO players2 VALUES(76561198177173167,'weiser',1539370842.1853001117,'ragnarok',746999.93799999996552,3296,1537205920.7565701008,45,'weiser#3768','',0,0,0,1,0,'ragnarok',0,'1538317751.991779',1,240,NULL,NULL,NULL);
DELETE FROM sqlite_sequence;
INSERT INTO sqlite_sequence VALUES('globalbuffer',1715);
INSERT INTO sqlite_sequence VALUES('lotteryinfo',40);
INSERT INTO sqlite_sequence VALUES('events',2);
COMMIT;
