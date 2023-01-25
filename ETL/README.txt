- Per builder l'immagine:

docker image build -t etl:0.0.1 / <DIRECTORY DOVE AVETE ESTRATTO LO ZIP> /ETL

(In caso cambiare 0.0.1 se nuova versione)

- Per eseguire l'immagine:

docker run -d  --log-opt max-size=500k --log-opt max-file=3 etl:0.0.1