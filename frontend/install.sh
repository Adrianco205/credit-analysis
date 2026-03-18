#!/bin/bash

echo "🌿 PerFinanzas - Instalación del Frontend"
echo "=========================================="
echo ""

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar Node.js
echo -e "${BLUE}📦 Verificando Node.js...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}⚠️ Node.js no está instalado. Por favor instala Node.js 18+${NC}"
    exit 1
fi

NODE_VERSION=$(node -v)
echo -e "${GREEN}✅ Node.js $NODE_VERSION detectado${NC}"
echo ""

# Instalar dependencias
echo -e "${BLUE}📦 Instalando dependencias...${NC}"
npm install

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Dependencias instaladas exitosamente${NC}"
else
    echo -e "${YELLOW}❌ Error al instalar dependencias${NC}"
    exit 1
fi

echo ""

# Configurar .env
if [ ! -f .env ]; then
    echo -e "${BLUE}⚙️ Configurando variables de entorno...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ Archivo .env creado${NC}"
    echo -e "${YELLOW}⚠️ Recuerda configurar NEXT_PUBLIC_API_URL en el archivo .env${NC}"
else
    echo -e "${GREEN}✅ Archivo .env ya existe${NC}"
fi

echo ""
echo -e "${GREEN}🎉 ¡Instalación completada!${NC}"
echo ""
echo "Para iniciar el servidor de desarrollo:"
echo -e "${BLUE}  npm run dev${NC}"
echo ""
echo "La aplicación estará disponible en:"
echo -e "${BLUE}  http://localhost:3000${NC}"
echo ""

