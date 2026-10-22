export interface CollectionItem { code:string; kind:"badge"|"theme"; title:string; game:string; description:string; unlocked:boolean; unlocked_at:string|null }
export interface CollectionState { active_badge:string|null; active_theme:string|null; items:CollectionItem[] }
