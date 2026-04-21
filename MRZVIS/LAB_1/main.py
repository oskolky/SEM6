#   Лабораторная работа №1 по дисциплине МРЗвИС
#   Задача: реализовать и исследовать модель решения на конвейерной архитектуре задачи
#   вычисления попарного частного компонентов двух векторов чисел
#   Вариант: 11. Алгоритм вычисления целочисленного частного пары 6-разрядных чисел
#   делением с восстановлением частичного остатка
#
#   Автор: Головач В.Д. (321703)
#
#   Используемые источники: https://libeldoc.bsuir.by/handle/123456789/42611

import os

p = 6             # разрядность операндов
conveyor_len = p  # длина конвейера = числу разрядов частного

# Индексы полей в элементе конвейера:
# [dividend, divisor, partial_remainder, quotient, dividend_shifted]
dnd_i  = 0   # исходное делимое (не меняется, для отображения)
dvs_i  = 1   # делитель (не меняется)
pr_i   = 2   # частичный остаток (расширенный, p+1 бит)
qt_i   = 3   # накапливаемое частное
dsh_i  = 4   # делимое, которое сдвигается влево на каждом шаге



# Алгоритм (шаг i, i=0 — старший бит частного):
#   1. Взять старший бит текущего сдвинутого делимого
#   2. Сдвинуть частичный остаток влево на 1, вдвинув этот бит справа
#   3. Сдвинуть делимое влево (следующий шаг возьмёт следующий бит)
#   4. Пробное вычитание: trial = remainder - divisor
#   5. Если trial >= 0: остаток = trial, бит частного = 1
#      Если trial <  0: остаток не меняется (восстановление), бит частного = 0
def process_step(stage_index: int, divisor: int,
                 partial_remainder: int, quotient: int, dividend_shifted: int):
    mask_p1 = (1 << (p + 1)) - 1

    # Старший бит текущего делимого (бит p-1)
    incoming_bit = (dividend_shifted >> (p - 1)) & 1

    # Сдвигаем остаток влево и вдвигаем бит делимого
    partial_remainder = ((partial_remainder << 1) | incoming_bit) & mask_p1

    # Сдвигаем делимое влево (для следующего этапа)
    dividend_shifted = (dividend_shifted << 1) & mask_p1

    # Пробное вычитание
    trial = partial_remainder - divisor

    bit_position = p - 1 - stage_index  # позиция в частном

    if trial >= 0:
        partial_remainder = trial
        quotient = quotient | (1 << bit_position)
    # иначе — восстановление: partial_remainder не меняется, бит остаётся 0

    return partial_remainder, quotient, dividend_shifted


# Визуализация конвейера
def print_conv(conv_data, tact_num, binary_pairs_str):
    os.system('cls')
    print(f"Входные данные:\n{binary_pairs_str}")
    print("\nКонвейер")
    print("=" * 100)
    print(f"{'Такт ' + str(tact_num + 1):^100}")
    print("=" * 100)

    for i, data in enumerate(conv_data):
        if data is not None:
            dividend          = data[dnd_i]
            divisor           = data[dvs_i]
            partial_remainder = data[pr_i]
            quotient          = data[qt_i]

            dividend_bin = bin(dividend)[2:].zfill(p)
            divisor_bin  = bin(divisor)[2:].zfill(p)
            pr_bin       = bin(partial_remainder)[2:].zfill(p + 1)
            qt_bin       = bin(quotient)[2:].zfill(p)
            bit_pos      = p - 1 - i

            print(f"  Этап {i + 1}  [бит частного № {bit_pos}]:")
            print(f"    Делимое:             {dividend_bin} ({dividend})")
            print(f"    Делитель:            {divisor_bin}  ({divisor})")
            print(f"    Частичный остаток:   {pr_bin} ({partial_remainder})")
            print(f"    Частное (пока):      {qt_bin} ({quotient})")
        else:
            print(f"  Этап {i + 1}: [пусто]")
        print("-" * 100)



# Один такт конвейера
conv_data = [None] * conveyor_len


def conveyor_stage(input_data, tact_num, binary_pairs_str):
    global conv_data

    # Сдвигаем данные по конвейеру
    for i in range(conveyor_len - 1, 0, -1):
        conv_data[i] = conv_data[i - 1]
    conv_data[0] = input_data

    # Обрабатываем каждый занятый этап
    for i, data_unit in enumerate(conv_data):
        if data_unit is not None:
            conv_data[i][pr_i], conv_data[i][qt_i], conv_data[i][dsh_i] = process_step(
                i,
                conv_data[i][dvs_i],
                conv_data[i][pr_i],
                conv_data[i][qt_i],
                conv_data[i][dsh_i]
            )

    print_conv(conv_data, tact_num, binary_pairs_str)

    # Если на последнем этапе есть данные — возвращаем результат
    if conv_data[-1] is not None:
        return conv_data[-1][qt_i]
    return None

# Обработка всех пар
def process_all(inputs, binary_pairs_str):
    results = []
    m = len(inputs)
    total_tacts = conveyor_len + m - 1

    for tact in range(total_tacts):
        input_data = inputs[tact] if tact < m else None
        result = conveyor_stage(input_data, tact, binary_pairs_str)

        if result is not None:
            pair_index = tact - conveyor_len + 1
            dividend = inputs[pair_index][dnd_i]
            divisor  = inputs[pair_index][dvs_i]
            expected = dividend // divisor
            results.append({
                "pair":     pair_index + 1,
                "dividend": dividend,
                "divisor":  divisor,
                "quotient": result,
                "expected": expected,
            })

        print("\nРезультаты:")
        for r in results:
            mark = "✓" if r["quotient"] == r["expected"] else "✗"
            print(f"  Пара {r['pair']}: {r['dividend']} ÷ {r['divisor']} = {r['quotient']} "
                  f"(ожидалось: {r['expected']}) {mark}")

        input("\nНажмите Enter для следующего такта...")

    return results

# Ввод данных
def parse_binary(string_num: str) -> int:
    if len(string_num) > p:
        raise ValueError(f"Число должно быть не более {p} разрядов")
    for ch in string_num:
        if ch not in ('0', '1'):
            raise ValueError("Введите число в двоичной системе (только 0 и 1)")
    return int(string_num, 2)


m = int(input("Введите количество пар чисел: "))

binary_pairs = []
for i in range(m):
    print(f"\nПара {i + 1}:")
    while True:
        try:
            dividend_str = input("  Введите делимое  (до 6 двоичных разрядов): ")
            divisor_str  = input("  Введите делитель (до 6 двоичных разрядов): ")
            dividend = parse_binary(dividend_str)
            divisor  = parse_binary(divisor_str)
            if divisor == 0:
                print("  Делитель не может быть равен нулю.")
                continue
            break
        except ValueError as e:
            print(f"  Ошибка: {e}. Повторите ввод.")


    binary_pairs.append([dividend, divisor, 0, 0, dividend])
    # [делимое, делитель, частичный_остаток=0, частное=0, делимое_для_сдвига]

binary_pairs_str = "\n".join(
    f"  Пара {i + 1}: Делимое = {bin(pair[dnd_i])[2:].zfill(p)} ({pair[dnd_i]}), "
    f"Делитель = {bin(pair[dvs_i])[2:].zfill(p)} ({pair[dvs_i]})"
    for i, pair in enumerate(binary_pairs)
)

print(f"\nВходные данные:\n{binary_pairs_str}\n")
input("Нажмите Enter для запуска конвейера...")

conv_data = [None] * conveyor_len

results = process_all(binary_pairs, binary_pairs_str)

# Итог
print("\n" + "=" * 60)
print("ИТОГОВЫЕ РЕЗУЛЬТАТЫ:")
print("=" * 60)
for r in results:
    mark = "✓" if r["quotient"] == r["expected"] else "✗"
    print(f"  Пара {r['pair']}: {r['dividend']} ÷ {r['divisor']} = {r['quotient']} "
          f"(проверка: {r['expected']}) {mark}")

K = (m * conveyor_len) / (conveyor_len + m - 1)
print(f"\nКоэффициент ускорения конвейера К = {K:.4f}")
print(f"  (при m={m} парах и длине конвейера {conveyor_len})")