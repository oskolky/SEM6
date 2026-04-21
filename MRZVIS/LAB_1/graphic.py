#   Лабораторная работа №1 по дисциплине МРЗвИС
#   Задача: реализовать и исследовать модель решения на конвейерной архитектуре задачи
#   вычисления попарного произведения компонентов двух векторов чисел
#   Вариант: 11. Алгоритм вычисления целочисленного частного пары 6-разрядных чисел
#   делением с восстановлением частичного остатка
#
#   Автор: Головач В.Д. (321703)



import matplotlib.pyplot as plt
import numpy as np

n_values = [1, 6]
r_values = [1, 2, 4, 6, 8, 10, 12, 16, 20, 26, 32, 38, 44, 50]

acceleration_data = []
efficiency_data = []

for n in n_values:
    acceleration_row = []
    efficiency_row = []

    for r in r_values:
        print(f"Измерение: n={n}, r={r}")

        try:
            T1 = n * r
            Tn = n + r - 1
            if Tn > 0:
                K = T1 / Tn
            else:
                K = 0

            acceleration_row.append(K)

            if n > 0:
                E = K / n
            else:
                E = 0

            efficiency_row.append(E)

            print(f"  T1={T1:.6f}, Tn={Tn:.6f}, K={K:.3f}, E={E:.3f}")
        except Exception as e:
            print(f"  Ошибка: {e}")
            acceleration_row.append(0)
            efficiency_row.append(0)

    acceleration_data.append(acceleration_row)
    efficiency_data.append(efficiency_row)

acceleration_data = np.array(acceleration_data)
efficiency_data = np.array(efficiency_data)

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

ax1 = axes[0, 0]
for i, n in enumerate(n_values):
    ax1.plot(r_values, acceleration_data[i], marker='o', label=f'Конвейер с n={n} этапами')
ax1.set_xlabel('Ранг задачи (r)')
ax1.set_ylabel('Коэффициент ускорения (Kу)')
ax1.set_title('Зависимость ускорения от ранга задачи')
ax1.legend()
ax1.grid(True, alpha=0.3)

ax2 = axes[0, 1]
for i, r in enumerate(r_values):
    ax2.plot(n_values, acceleration_data[:, i], marker='s', linestyle='none', label=f'r={r}')
ax2.set_xlabel('Количество процессорных элементов (n)')
ax2.set_ylabel('Коэффициент ускорения (Kу)')
ax2.set_title('Зависимость ускорения от количества ПЭ')
ax2.legend()
ax2.grid(True, alpha=0.3)

ax3 = axes[1, 0]
for i, n in enumerate(n_values):
    ax3.plot(r_values, efficiency_data[i], marker='o', label=f'Конвейер с n={n} этапами')
ax3.set_xlabel('Ранг задачи (r)')
ax3.set_ylabel('Эффективность (E)')
ax3.set_title('Зависимость эффективности от ранга задачи')
ax3.legend()
ax3.grid(True, alpha=0.3)

ax4 = axes[1, 1]
for i, r in enumerate(r_values):
    ax4.plot(n_values, efficiency_data[:, i], marker='s', linestyle='none', label=f'r={r}')
ax4.set_xlabel('Количество процессорных элементов (n)')
ax4.set_ylabel('Эффективность (E)')
ax4.set_title('Зависимость эффективности от количества ПЭ')
ax4.legend()
ax4.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()