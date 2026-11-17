# Bănci

Clasificatorul băncilor din Moldova și România, cu **BIC / SWIFT**, codul din IBAN, IDNO / CUI, adresa și telefonul.
Din el se alege banca la conturile bancare ale instituției (*Constante → Conturi bancare*).

## Listele oficiale
Băncile se încarcă singure la instalare:
- **Moldova** — băncile licențiate (BNM), plus Trezoreria de Stat și BNM;
- **România** — codurile BIC (TransFond), CUI și sediile (registrul ASF), plus băncile fuzionate, pentru IBAN-urile
  vechi (de ex. OTP Bank România → Banca Transilvania).

Bifați țările folosite și **Încarcă / actualizează** ca să aduceți lista din versiunea nouă a programului. Debifat =
băncile țării se scot din clasificator. Băncile adăugate de mână rămân mereu. Conturile bancare păstrează banca scrisă.

## Banca după IBAN
La scrierea IBAN-ului banca și BIC-ul se completează singure: după IBAN, din **Cod IBAN** — identificatorul băncii
de după cifrele de control (Moldova: 2 caractere, AG = maib; România: 4, BTRL = Banca Transilvania). Denumirea scrisă
de mână nu se schimbă.

Lângă câmpul **Banca** butonul **…** deschide lista cu căutare (denumire, BIC, IDNO); clic pe rând = se pun denumirea
și BIC-ul.

## Banca nouă
**Bancă nouă** — pentru o bancă din altă țară sau una care lipsește: țara, BIC / SWIFT, codul din IBAN (ca să se
recunoască din IBAN), denumirea, IDNO / CUI, adresa, contactele.
