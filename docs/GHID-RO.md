# De la cameră la un portret salvat

Proiectul este pregătit pentru a fi dat unui agent AI: trimite-i arhiva sau linkul
GitHub și cere-i să citească `AGENTS.md`. Codul și pașii sunt incluși; cheia API,
modelele și mediul Python trebuie completate pe calculatorul tău.

Nu există pagină web, interfață de administrare, sunet sau vizualizările
instalației. Sunt doar modulele Python și câteva comenzi pentru rularea lor.

## Pașii

1. Instalează Python 3.11 sau mai nou și creează mediul izolat din
   [SETUP.md](SETUP.md). Instalează pachetul și rulează testele, fără cameră/API.
2. Descarcă separat Qwen3-VL-4B în format GGUF și proiectorul vizual compatibil.
   Instalează llama.cpp și pornește modelul numai pe `127.0.0.1:8795`, conform
   instrucțiunilor. Fișierele modelelor nu se află în arhivă.
3. Rulează `python -m portrait_seed doctor` pentru a verifica serviciul local.
4. Cu acordul persoanei, rulează
   `python -m portrait_seed describe --camera 0 --consent`.
   Fotografia este analizată local; comanda afișează un ID pentru descriere.
5. Introdu propria cheie OpenAI într-un prompt local ascuns, conform SETUP.md.
   Nu o trimite agentului în chat și nu o adăuga în fișierele publice.
6. În maximum zece minute de la captură, rulează
   `python -m portrait_seed resume ID --allow-paid`.
   Opțiunea permite maximum trei încercări taxabile pentru captura respectivă.
7. Portretul rezultat se găsește în `private-data/portraits`, alături de descrierea
   sa JSON. Următoarea generare poate continua de la acest portret. Pentru o
   colecție independentă, folosește un alt director prin opțiunea `--data`.

## Ce demonstrează codul

Fotografia merge către modelul local. OpenAI primește descrierea și, la editare,
un portret generat anterior, verificat în colecția proprie. Testele inspectează
acest traseu folosind imagini sintetice și răspunsuri simulate.

Pachetul nu scrie fotografii ale vizitatorilor pe disc. Procesul care le folosește
este închis după analiză sau oprit la termenul de zece minute. Memoria serverului
Qwen și mecanismele sistemului de operare au propriul ciclu de viață; nu promitem
ștergere criminalistică a memoriei sau a discului.

Descrierile și portretele generate se păstrează și pot conține informații
personale. Acest proiect redus nu creează embeddinguri sau o memorie a
identităților. Instalația completă are componente suplimentare, explicate în
[proveniență](PROVENANCE.md) și în
[articolul SIDECUBE](https://sidecube.ro/revista/feature-fusion/).

## Pentru publicare

Agentul care publică trebuie să urmeze [PUBLISH.md](../PUBLISH.md), să verifice
arhiva și să folosească doar acest director. Numele propus este `portrait-seed`.
Licența MIT permite reutilizarea cu păstrarea creditului Deian Berar.
Fișierele modelelor, cheile și datele generate de utilizatori nu se publică.

