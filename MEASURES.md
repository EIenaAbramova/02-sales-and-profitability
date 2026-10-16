# Меры DAX

Формулы выгружены из модели версии с обычным кликом. Всего 32 меры: 17 бизнес-мер, 2 меры переключения, 12 мер цвета и 1 SVG-мера карты.

## Выручка

Сумма выручки по строкам продаж в текущем контексте фильтров.

```dax
Выручка =
SUM('f_Продажи'[Revenue])
```

## Прибыль

Сумма прибыли по строкам продаж.

```dax
Прибыль =
SUM('f_Продажи'[Profit])
```

## Рентабельность

Прибыль / выручка. Итог вычисляется как отношение сумм, а не среднее процентов строк.

```dax
Рентабельность =
DIVIDE([Прибыль], [Выручка])
```

## АКБ

Количество уникальных покупателей, совершивших покупки в выбранном контексте.

```dax
АКБ =
DISTINCTCOUNT('f_Продажи'[Buyer])
```

## Заказы

Количество уникальных идентификаторов заказов.

```dax
Заказы =
DISTINCTCOUNT('f_Продажи'[Order_ID])
```

## Средний чек

Выручка / количество уникальных заказов. Один заказ может содержать несколько строк.

```dax
Средний чек =
DIVIDE([Выручка], [Заказы])
```

## Затраты на логистику

Стоимость способа доставки начисляется на каждую строку продаж по приложенному чек-листу.

```dax
Затраты на логистику =
SUMX('f_Продажи', RELATED('d_Доставка'[Стоимость]))
```

## Убыточные заказы

Количество заказов с отрицательной суммарной прибылью в текущем контексте. Отрицательная строка сама по себе не делает весь заказ убыточным.

```dax
Убыточные заказы =
VAR T = FILTER(VALUES('f_Продажи'[Order_ID]), CALCULATE([Прибыль]) < 0)
RETURN COUNTROWS(T)
```

## Прибыль убыточных заказов

Суммарная прибыль только заказов, попавших в множество убыточных.

```dax
Прибыль убыточных заказов =
VAR T = FILTER(VALUES('f_Продажи'[Order_ID]), CALCULATE([Прибыль]) < 0)
RETURN SUMX(T, CALCULATE([Прибыль]))
```

## Ранг товара

Плотный ранг товара по выручке среди выбранного набора товаров.

```dax
Ранг товара =
IF(ISINSCOPE('d_Продукты'[Product]),
RANKX(ALLSELECTED('d_Продукты'), [Выручка], , DESC, DENSE))
```

## Доля товара

Доля выручки товара в выручке выбранного набора товаров.

```dax
Доля товара =
IF(ISINSCOPE('d_Продукты'[Product]),
DIVIDE([Выручка], CALCULATE([Выручка], ALLSELECTED('d_Продукты'))))
```

## Накопленная доля

Накопленная доля выручки по убыванию продаж. При равной выручке используется название товара для детерминированного порядка.

```dax
Накопленная доля =
VAR CurrentProduct = SELECTEDVALUE('d_Продукты'[Product])
VAR CurrentRevenue = [Выручка]
VAR Universe = FILTER(ADDCOLUMNS(ALLSELECTED('d_Продукты'), "@Revenue", CALCULATE([Выручка])), [@Revenue] > 0)
VAR Running = SUMX(FILTER(Universe, [@Revenue] > CurrentRevenue ||
    ([@Revenue] = CurrentRevenue && 'd_Продукты'[Product] <= CurrentProduct)), [@Revenue])
RETURN IF(ISINSCOPE('d_Продукты'[Product]), DIVIDE(Running, SUMX(Universe, [@Revenue])))
```

## ABC товара

Класс товара по накопленной доле ДО текущего товара. Пересекающий 80% или 95% товар относится к предыдущей группе.

```dax
ABC товара =
VAR CurrentProduct = SELECTEDVALUE('d_Продукты'[Product])
VAR CurrentRevenue = [Выручка]
VAR Universe = FILTER(ADDCOLUMNS(ALLSELECTED('d_Продукты'), "@Revenue", CALCULATE([Выручка])), [@Revenue] > 0)
VAR RevenueBefore = SUMX(FILTER(Universe, [@Revenue] > CurrentRevenue ||
    ([@Revenue] = CurrentRevenue && 'd_Продукты'[Product] < CurrentProduct)), [@Revenue])
VAR ShareBefore = DIVIDE(COALESCE(RevenueBefore, 0), SUMX(Universe, [@Revenue]))
RETURN IF(ISINSCOPE('d_Продукты'[Product]) && CurrentRevenue > 0,
    SWITCH(TRUE(), ShareBefore < 0.8, "A", ShareBefore < 0.95, "B", "C"))
```

## Выручка ABC

Выручка товаров выбранного класса ABC, вычисленного заново в контексте фильтров.

```dax
Выручка ABC =
VAR SelectedClasses = VALUES('d_ABC'[ABC])
VAR Universe = FILTER(ADDCOLUMNS(ALLSELECTED('d_Продукты'), "@Revenue", CALCULATE([Выручка])), [@Revenue] > 0)
VAR TotalRevenue = SUMX(Universe, [@Revenue])
VAR Classified = ADDCOLUMNS(Universe, "@Class",
    VAR P = 'd_Продукты'[Product]
    VAR V = [@Revenue]
    VAR RevenueBefore = SUMX(FILTER(Universe, [@Revenue] > V || ([@Revenue] = V && 'd_Продукты'[Product] < P)), [@Revenue])
    VAR ShareBefore = DIVIDE(COALESCE(RevenueBefore, 0), TotalRevenue)
    RETURN SWITCH(TRUE(), ShareBefore < 0.8, "A", ShareBefore < 0.95, "B", "C"))
VAR ChosenProducts = SELECTCOLUMNS(FILTER(Classified, [@Class] IN SelectedClasses), "Product", 'd_Продукты'[Product])
RETURN CALCULATE([Выручка], KEEPFILTERS(TREATAS(ChosenProducts, 'd_Продукты'[Product])))
```

## Прибыль ABC

Прибыль товаров выбранного класса ABC.

```dax
Прибыль ABC =
VAR SelectedClasses = VALUES('d_ABC'[ABC])
VAR Universe = FILTER(ADDCOLUMNS(ALLSELECTED('d_Продукты'), "@Revenue", CALCULATE([Выручка])), [@Revenue] > 0)
VAR TotalRevenue = SUMX(Universe, [@Revenue])
VAR Classified = ADDCOLUMNS(Universe, "@Class",
    VAR P = 'd_Продукты'[Product]
    VAR V = [@Revenue]
    VAR RevenueBefore = SUMX(FILTER(Universe, [@Revenue] > V || ([@Revenue] = V && 'd_Продукты'[Product] < P)), [@Revenue])
    VAR ShareBefore = DIVIDE(COALESCE(RevenueBefore, 0), TotalRevenue)
    RETURN SWITCH(TRUE(), ShareBefore < 0.8, "A", ShareBefore < 0.95, "B", "C"))
VAR ChosenProducts = SELECTCOLUMNS(FILTER(Classified, [@Class] IN SelectedClasses), "Product", 'd_Продукты'[Product])
RETURN CALCULATE([Прибыль], KEEPFILTERS(TREATAS(ChosenProducts, 'd_Продукты'[Product])))
```

## АКБ ABC

Уникальные покупатели товаров выбранного класса; покупатели разных классов могут пересекаться.

```dax
АКБ ABC =
VAR SelectedClasses = VALUES('d_ABC'[ABC])
VAR Universe = FILTER(ADDCOLUMNS(ALLSELECTED('d_Продукты'), "@Revenue", CALCULATE([Выручка])), [@Revenue] > 0)
VAR TotalRevenue = SUMX(Universe, [@Revenue])
VAR Classified = ADDCOLUMNS(Universe, "@Class",
    VAR P = 'd_Продукты'[Product]
    VAR V = [@Revenue]
    VAR RevenueBefore = SUMX(FILTER(Universe, [@Revenue] > V || ([@Revenue] = V && 'd_Продукты'[Product] < P)), [@Revenue])
    VAR ShareBefore = DIVIDE(COALESCE(RevenueBefore, 0), TotalRevenue)
    RETURN SWITCH(TRUE(), ShareBefore < 0.8, "A", ShareBefore < 0.95, "B", "C"))
VAR ChosenProducts = SELECTCOLUMNS(FILTER(Classified, [@Class] IN SelectedClasses), "Product", 'd_Продукты'[Product])
RETURN CALCULATE([АКБ], KEEPFILTERS(TREATAS(ChosenProducts, 'd_Продукты'[Product])))
```

## Логистика ABC

Логистические расходы по строкам товаров выбранного класса.

```dax
Логистика ABC =
VAR SelectedClasses = VALUES('d_ABC'[ABC])
VAR Universe = FILTER(ADDCOLUMNS(ALLSELECTED('d_Продукты'), "@Revenue", CALCULATE([Выручка])), [@Revenue] > 0)
VAR TotalRevenue = SUMX(Universe, [@Revenue])
VAR Classified = ADDCOLUMNS(Universe, "@Class",
    VAR P = 'd_Продукты'[Product]
    VAR V = [@Revenue]
    VAR RevenueBefore = SUMX(FILTER(Universe, [@Revenue] > V || ([@Revenue] = V && 'd_Продукты'[Product] < P)), [@Revenue])
    VAR ShareBefore = DIVIDE(COALESCE(RevenueBefore, 0), TotalRevenue)
    RETURN SWITCH(TRUE(), ShareBefore < 0.8, "A", ShareBefore < 0.95, "B", "C"))
VAR ChosenProducts = SELECTCOLUMNS(FILTER(Classified, [@Class] IN SelectedClasses), "Product", 'd_Продукты'[Product])
RETURN CALCULATE([Затраты на логистику], KEEPFILTERS(TREATAS(ChosenProducts, 'd_Продукты'[Product])))
```

## Выбранный показатель

Возвращает одну из шести бизнес-мер по выбранному ID независимой таблицы «Показатели». При отсутствии выбора используется рентабельность.

```dax
Выбранный показатель =
VAR K = SELECTEDVALUE('Показатели'[ID], 4) RETURN SWITCH(K,0,[Выручка],1,[Прибыль],2,[АКБ],3,[Средний чек],4,[Рентабельность],5,[Затраты на логистику], [Рентабельность])
```

Динамическое выражение формата:

```dax
IF(SELECTEDVALUE('Показатели'[ID],4)=4, "0.00%", "#,0.00")
```

## Показатель для графиков

Переводит выручку, прибыль и средний чек в тысячи. Динамический формат показывает проценты для рентабельности и целые числа для АКБ и логистики.

```dax
Показатель для графиков =
VAR K = SELECTEDVALUE('Показатели'[ID],4) RETURN IF(K IN {0,1,3}, DIVIDE([Выбранный показатель],1000), [Выбранный показатель])
```

Динамическое выражение формата:

```dax
VAR K = SELECTEDVALUE('Показатели'[ID],4) RETURN SWITCH(TRUE(),K=4,"0.00%",K IN {0,1,3},"#,0.00 ""тыс.""","#,0")
```

## Фон KPI 0

Цвет нижней полосы карточки «Выручка»: чёрный, если выбран её ID, иначе белый.

```dax
Фон KPI 0 =
IF(SELECTEDVALUE('Показатели'[ID],4)=0, "#333333", "#FFFFFF")
```

## Текст KPI 0

Контрастный цвет подписи карточки «Выручка»: белый на активной чёрной полосе, иначе тёмный.

```dax
Текст KPI 0 =
IF(SELECTEDVALUE('Показатели'[ID],4)=0, "#FFFFFF", "#252423")
```

## Фон KPI 1

Цвет нижней полосы карточки «Прибыль»: чёрный, если выбран её ID, иначе белый.

```dax
Фон KPI 1 =
IF(SELECTEDVALUE('Показатели'[ID],4)=1, "#333333", "#FFFFFF")
```

## Текст KPI 1

Контрастный цвет подписи карточки «Прибыль»: белый на активной чёрной полосе, иначе тёмный.

```dax
Текст KPI 1 =
IF(SELECTEDVALUE('Показатели'[ID],4)=1, "#FFFFFF", "#252423")
```

## Фон KPI 2

Цвет нижней полосы карточки «АКБ»: чёрный, если выбран её ID, иначе белый.

```dax
Фон KPI 2 =
IF(SELECTEDVALUE('Показатели'[ID],4)=2, "#333333", "#FFFFFF")
```

## Текст KPI 2

Контрастный цвет подписи карточки «АКБ»: белый на активной чёрной полосе, иначе тёмный.

```dax
Текст KPI 2 =
IF(SELECTEDVALUE('Показатели'[ID],4)=2, "#FFFFFF", "#252423")
```

## Фон KPI 3

Цвет нижней полосы карточки «Средний чек»: чёрный, если выбран её ID, иначе белый.

```dax
Фон KPI 3 =
IF(SELECTEDVALUE('Показатели'[ID],4)=3, "#333333", "#FFFFFF")
```

## Текст KPI 3

Контрастный цвет подписи карточки «Средний чек»: белый на активной чёрной полосе, иначе тёмный.

```dax
Текст KPI 3 =
IF(SELECTEDVALUE('Показатели'[ID],4)=3, "#FFFFFF", "#252423")
```

## Фон KPI 4

Цвет нижней полосы карточки «Рентабельность»: чёрный, если выбран её ID, иначе белый.

```dax
Фон KPI 4 =
IF(SELECTEDVALUE('Показатели'[ID],4)=4, "#333333", "#FFFFFF")
```

## Текст KPI 4

Контрастный цвет подписи карточки «Рентабельность»: белый на активной чёрной полосе, иначе тёмный.

```dax
Текст KPI 4 =
IF(SELECTEDVALUE('Показатели'[ID],4)=4, "#FFFFFF", "#252423")
```

## Фон KPI 5

Цвет нижней полосы карточки «Затраты на логистику»: чёрный, если выбран её ID, иначе белый.

```dax
Фон KPI 5 =
IF(SELECTEDVALUE('Показатели'[ID],4)=5, "#333333", "#FFFFFF")
```

## Текст KPI 5

Контрастный цвет подписи карточки «Затраты на логистику»: белый на активной чёрной полосе, иначе тёмный.

```dax
Текст KPI 5 =
IF(SELECTEDVALUE('Показатели'[ID],4)=5, "#FFFFFF", "#252423")
```

## Карта регионов

Техническая мера формирует SVG с границами провинций, категория данных `ImageUrl`. Полное выражение включено в [measures.dax](measures.dax). Используется выбранный KPI: для рентабельности цвет зависит от значения, для остальных показателей — от отношения значения региона к общему значению. Для средних и уникальных покупателей такие отношения не обязаны суммироваться в 100%.
