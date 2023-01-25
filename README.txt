Informazioni per build e deploy
Per windows e Mac: 
-	Entrare nella Directory del progetto
-	docker image build -t etl:0.0.1 ./ETL/
-	docker image build -t datastorage:0.0.1 ./DataStorage/
-	docker image build -t dataretrieval:0.0.1 ./DataRetrieval/
-	docker image build -t slamanager:0.0.1 ./SLAManager/
-	Docker compose up –d
Qualora non funzionasse la libreria confluent-kafka, modificare il dockerfile aggiornando la versione di python alla 3.10.8.
Per Mac con processore ARM Apple Silicon:
Aggiungere nei docker file di ETL, DataStorage:
•	RUN apt update && apt -y install software-properties-common gcc
•	RUN git clone https://github.com/edenhill/librdkafka
•	RUN cd librdkafka && ./configure && make && make install && ldconfig
I precedenti comandi nei dockerfile di interesse sono commentati, basta rimuovere il simbolo #
-	Entrare nella Directory del progetto
-	docker image build -t etl:0.0.1 ./ETL/
-	docker image build -t datastorage:0.0.1 ./DataStorage/
-	docker image build -t dataretrieval:0.0.1 ./DataRetrieval/
-	docker image build -t slamanager:0.0.1 ./SLAManager/
-	Docker compose up –d
