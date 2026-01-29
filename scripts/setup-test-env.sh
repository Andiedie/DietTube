#!/bin/bash
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

DATA_DIR="$PROJECT_ROOT/data"
SOURCE_DIR="$DATA_DIR/source"
TEMP_DIR="$DATA_DIR/temp"
CONFIG_DIR="$DATA_DIR/config"
DB_FILE="$CONFIG_DIR/diettube.db"
VIDEO_FILE="$PROJECT_ROOT/video.mp4"

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}  DietTube 测试环境初始化脚本${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""
echo -e "${RED}警告: 此脚本将执行以下操作:${NC}"
echo "  1. 清空 $SOURCE_DIR"
echo "  2. 清空 $TEMP_DIR"
echo "  3. 删除数据库 $DB_FILE"
echo "  4. 创建测试目录结构并复制测试视频"
echo ""

# 检查 video.mp4 是否存在
if [ ! -f "$VIDEO_FILE" ]; then
    echo -e "${RED}错误: 测试视频文件不存在: $VIDEO_FILE${NC}"
    exit 1
fi

# 确认提示
read -p "确定要继续吗? (输入 yes 确认): " confirm
if [ "$confirm" != "yes" ]; then
    echo "已取消操作"
    exit 0
fi

echo ""
echo -e "${GREEN}开始初始化测试环境...${NC}"

# 清空 source 目录
echo "清空 source 目录..."
rm -rf "$SOURCE_DIR"
mkdir -p "$SOURCE_DIR"

# 清空 temp 目录
echo "清空 temp 目录..."
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

# 删除数据库
echo "删除数据库..."
rm -f "$DB_FILE"

# 创建测试目录结构
echo "创建测试目录结构..."

# 根目录视频
cp "$VIDEO_FILE" "$SOURCE_DIR/root_video.mp4"

# 一级目录
mkdir -p "$SOURCE_DIR/Movies"
cp "$VIDEO_FILE" "$SOURCE_DIR/Movies/movie_sample.mp4"

mkdir -p "$SOURCE_DIR/TV Shows"
cp "$VIDEO_FILE" "$SOURCE_DIR/TV Shows/episode_01.mp4"

# 二级目录
mkdir -p "$SOURCE_DIR/Movies/Action"
cp "$VIDEO_FILE" "$SOURCE_DIR/Movies/Action/action_movie.mp4"

mkdir -p "$SOURCE_DIR/Movies/Comedy"
cp "$VIDEO_FILE" "$SOURCE_DIR/Movies/Comedy/comedy_movie.mp4"

mkdir -p "$SOURCE_DIR/TV Shows/Breaking Bad"
cp "$VIDEO_FILE" "$SOURCE_DIR/TV Shows/Breaking Bad/S01E01.mp4"
cp "$VIDEO_FILE" "$SOURCE_DIR/TV Shows/Breaking Bad/S01E02.mp4"

# 三级目录
mkdir -p "$SOURCE_DIR/TV Shows/Breaking Bad/Season 1"
cp "$VIDEO_FILE" "$SOURCE_DIR/TV Shows/Breaking Bad/Season 1/Episode_01.mp4"
cp "$VIDEO_FILE" "$SOURCE_DIR/TV Shows/Breaking Bad/Season 1/Episode_02.mp4"

mkdir -p "$SOURCE_DIR/TV Shows/Breaking Bad/Season 2"
cp "$VIDEO_FILE" "$SOURCE_DIR/TV Shows/Breaking Bad/Season 2/Episode_01.mp4"

# 特殊字符目录名
mkdir -p "$SOURCE_DIR/电影"
cp "$VIDEO_FILE" "$SOURCE_DIR/电影/中文电影.mp4"

mkdir -p "$SOURCE_DIR/Movies/2024 (New)"
cp "$VIDEO_FILE" "$SOURCE_DIR/Movies/2024 (New)/new_release.mp4"

# 不同扩展名
cp "$VIDEO_FILE" "$SOURCE_DIR/Movies/sample.mkv"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  测试环境初始化完成!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "创建的测试文件:"
find "$SOURCE_DIR" -type f -name "*.mp4" -o -name "*.mkv" | sort | while read f; do
    echo "  - ${f#$SOURCE_DIR/}"
done
echo ""
echo "共 $(find "$SOURCE_DIR" -type f | wc -l | tr -d ' ') 个测试文件"
echo ""
echo -e "${YELLOW}提示: 启动后端服务后，访问 Dashboard 点击「扫描视频」开始测试${NC}"
