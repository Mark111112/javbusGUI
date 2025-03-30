# JavBus Web - Docker版

这是JavBus应用程序的Docker版本，允许通过Web浏览器访问JavBus的功能。原应用程序不再更新。
你还是需要一个https://github.com/ovnrain/javbus-api来获得API URL。感谢作者。

## 功能特性

1. 输入番号或演员名称进行查询，输出电影列表
2. 不输入任何信息查询时，输出首页的电影列表
3. 点击影片进入影片详情页面，展示封面图、预览图、厂牌、类别、演员等信息，点击相关信息进一步搜索
4. 显示和复制磁力链接
5. 获取影片简介（部分影片需要自定义fanza对应）
6. 对影片标题和简介进行翻译（调用在线API，需要输入API token）
7. 跳转到missav的相应页面在线观影

## 快速开始

### 前提条件

- 安装 [Docker](https://docs.docker.com/get-docker/)
- 安装 [Docker Compose](https://docs.docker.com/compose/install/)
- 取得一个javbus-api url

### 使用Docker Compose部署

1. 克隆或下载本仓库到本地
2. 进入项目目录
3. 创建`.env`文件并设置API_URL环境变量（可选）
4. 使用Docker Compose启动应用

```bash
# 克隆仓库
git clone <仓库地址>
cd dock-2_javbus

# 使用Docker Compose构建和启动
docker-compose up -d
```

### 手动构建和运行Docker镜像

如果你不想使用Docker Compose，也可以手动构建和运行：

```bash
# 构建Docker镜像
docker build -t dock-2_javbus .

# 运行容器
docker run -d -p 9080:8080 -v /docker/dock-2_javbus/buspic /app/buspic -v /docker/dock-2_javbus/config /app/config -v /docker/dock-2_javbus/data /app/data --name dock-2_javbus furey79:dock-2_javbus
```

## 访问应用

应用启动后，通过浏览器访问 http://localhost:9080 即可使用。

首次使用时，你需要在页面顶部设置API地址，然后点击"检查API"按钮以验证连接。

## 数据持久化

应用默认将数据存储在容器内的SQLite数据库中。如果你想持久化数据，可以挂载一个卷：

```bash
docker run -d -p 9080:8080 \
  -v ./data:/app/data \
  -v ./buspic:/app/buspic \
  -v ./config:/app/config \
  -e API_URL="你的API地址" \
  --name dock-2_javbus furey79:dock-2_javbus
```

## 自定义配置

你可以通过网页配置按钮修改`config.json`文件来自定义应用配置：

```json
{
  "api_url": "你的API地址",
  "watch_url_prefix": "https://missav.ai"
}
```

## 注意事项

- 此应用需要一个有效的JavBus API地址才能正常工作
- 所有图片和数据都会缓存在本地，以提高性能
- 所有敏感内容仅供成年人使用，请遵守当地法律法规 
