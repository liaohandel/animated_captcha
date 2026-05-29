測試網頁(CAPTCHA-gui)伺服器架構

一、	Web api http://localhost:5000/ (docker container: captcha_web)
1.	/ 		index.html       [Animated CAPTCHA Test GUI  ];
2.	/ setgui	             setweb.html      [Animated CAPTCHA Build TOOL];
3.	/ dataset  	dataset_gui.html [Animated CAPTCHA  DataSet   ];
4.	/getpasswd	get_password_api()   [get passwd json by Agents accest] ;

二、	MySQL#MaridDB  (docker container: ,captcha_db)
1.	Ip = http://localhost:3306;
2.	DB = passwddb , Table =userlog   ;
3.	DB = passwddb , Table=datasetlog;
   
三、	Web api ( http://localhost:5100/): (docker container:  agent_client) Agent 對驗證碼操作的中繼工具 Agent_client_Tool  三功能(圖 4.8)。
1.	Working 驅動測試工具介面;
2.	DataSet 驅動測試工具介面;
3.	測試進度狀態顯示介面;

請Hermes 依上訴架構 使用 Docker-compse 建立 Captcha_gui , mariaDB , Agent-client 三個容器

<img width="1024" height="640" alt="Hermes-agent-flowchartx1" src="https://github.com/user-attachments/assets/6a045db5-f066-4f1a-ae1f-6db93f5abaa8" />

<img width="800" height="800" alt="sp_a5c2tenp6_033" src="https://github.com/user-attachments/assets/a840e8db-98a9-409f-a253-4ab1d5e02819" />

<img width="477" height="375" alt="image" src="https://github.com/user-attachments/assets/afdf093f-f3d3-4b81-a163-c6e6c96b3578" />


<img width="486" height="327" alt="image" src="https://github.com/user-attachments/assets/aa22ce20-dc9a-48df-8c9e-2d093c9d5547" />

<img width="982" height="1021" alt="image" src="https://github.com/user-attachments/assets/215409df-a64c-4913-b252-1bc0ac78e541" />

<img width="638" height="670" alt="image" src="https://github.com/user-attachments/assets/9aa03deb-9004-4148-99a1-38d089a2ecf5" />


