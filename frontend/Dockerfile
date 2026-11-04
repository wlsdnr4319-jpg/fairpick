# 프론트 빌드 결과를 Nginx 가 서빙하고, /api/ 는 API 로 넘긴다 (레퍼런스 14장).
# 프론트와 API 를 한 도메인에 묶어 쿠키·CORS 문제가 생기지 않는다.
FROM node:22-alpine AS build
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:stable-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist /usr/share/nginx/html
EXPOSE 80
