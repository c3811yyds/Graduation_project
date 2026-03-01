# 第一阶段：构建前端资源
FROM node:20-alpine as build-stage

WORKDIR /app

# 复制 package.json 相关文件，以利用缓存机制
COPY package*.json ./

# 设置 npm 国内镜像以加速安装
RUN npm set registry https://registry.npmmirror.com

# 安装依赖项
RUN npm install

# 复制整个项目
COPY . .

# 执行构建
RUN npm run build

# 第二阶段：使用 Nginx 提供服务
FROM nginx:alpine as production-stage

# 把构建后产生的前端静态文件复制到 Nginx 的网页目录
COPY --from=build-stage /app/dist /usr/share/nginx/html

# 复制 nginx 配置文件
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口给容器外
EXPOSE 80

# 启动 nginx 
CMD ["nginx", "-g", "daemon off;"]
