/** Fără diacritice și majuscule, pentru căutare: „campuri” găsește „Câmpuri obligatorii”, „localitati” — „Localități”. */
export const fold = (s: string) => s.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase()
