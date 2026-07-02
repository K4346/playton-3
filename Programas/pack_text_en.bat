@echo off

echo "Packing translated texts..."

cd ..

cd Programas

rem Pack main story texts
python pack_text.py txt "..\Textos Traduzidos\txt\uk" "..\Arquivos Traduzidos\txt\uk"

rem Pack puzzle texts (rc/nazo)
python pack_text.py rc "..\Textos Traduzidos\rc\nazo\uk" "..\Arquivos Traduzidos\rc\nazo\uk"

echo "Text packing complete!"
