"""
Задача о курильщиках (Smokers Problem)

Описание:
В данной реализации используется многопоточность для моделирования классической
задачи синхронизации — задачи о курильщиках.
Имеется агент и три курильщика.
У каждого курильщика бесконечный запас одного из ингредиентов: табак, бумага или спички.
Агент в случайном порядке выкладывает на стол два ингредиента.
Курильщик, у которого есть третий (недостающий),
может забрать ингредиенты со стола, скрутить сигарету и курить в течение 5 секунд.

Основные компоненты:
- Класс `Table` — реализует логику взаимодействия между агентом и курильщиками.
- Поток `agent` — бесконечно выкладывает ингредиенты.
- Потоки `smoker` — курильщики, которые ждут подходящих ингредиентов и курят.
- Используются `threading.Lock` и `threading.Condition` для синхронизации доступа.

Особенности:
- Во время курения (5 секунд) курильщик не может снова взять ингредиенты.
- Стол не может быть занят двумя наборами ингредиентов одновременно.
"""

import threading
import time
import random

INGREDIENTS = ["табак", "бумага", "спички"]


class Table:
    """
       Класс Table представляет общий ресурс — стол, на который агент кладёт ингредиенты.

       Атрибуты:
       - lock: блокировка для синхронизации доступа к ресурсу.
       - condition: условие для уведомления потоков о событиях (ожидание и оповещение).
       - ingredients: список из двух ингредиентов, которые в данный момент находятся на столе.
       - smoker_status: словарь, отслеживающий,
         курит ли сейчас курильщик с определённым ингредиентом.
       - table_busy: флаг, указывающий, занят ли стол (т.е. лежат ли на нём ингредиенты).

       Методы:
       - place_ingredients(first, second): агент кладёт два ингредиента на стол.
       - try_take(own_ingredient): курильщик проверяет,
         может ли он взять ингредиенты и начать курить.
       - finish_smoking(own_ingredient): вызывается по завершению курения, чтобы снять флаг "курит".

       О семафорах:
       Самое гавное: НЕ РАБОТЕТ С КОНТЕКСТНЫМ МЕНЕДЖЕРОМ with
       acquire() - ждёт, пока ресурс станет свободен, а затем захватывает его
       release() - освобождает ресурс, чтобы его могли занять
       """
    def __init__(self):
        """
        self.lock — блокировка для синхронизации доступа.
        self.condition — уведомление потоков
        self.ingredients — используется для обозначения того, что лежит на столе
        self.smoker_status — кто из курильщиков сейчас курит
        self.table_busy — есть ли что-то на столе.
        """

        self.table_mutex = threading.Semaphore(1)  # семафор — стол может быть занят только одним
        self.agent_sem = threading.Semaphore(1)  # агент может положить ингредиенты(стол свободен)
        self.smoker_sem = threading.Semaphore(0)  # семафор, чтобы будить всех курильщиков

        self.ingredients = []
        self.smoker_status = {ingredient: False for ingredient in INGREDIENTS}
        self.table_busy = False

    def place_ingredients(self, first, second):
        """
        Агент кладёт ингридиенты на стол
        :param first: первый ингридиент
        :param second: второй ингридиент
        """
        # агент не может положить ингредиенты, пока предыдущий набор не убран
        self.agent_sem.acquire()  # pylint: disable=consider-using-with
        # гарантирует, что только один поток может менять содержимое стола
        with self.table_mutex:
            self.ingredients = [first, second]
            self.table_busy = True
            print(f"Агент кладёт: {first} и {second}")
        # будим одного из курильщиков
        self.smoker_sem.release()

    def try_take(self, own_ingredient):
        """
        Курильщик пытается взять ингридиенты
        :param own_ingredient: один из ингридиентов(табак, бумага, спички)
        :return:
        """
        with self.table_mutex:
            needed = set(INGREDIENTS) - {own_ingredient}
            if (
                    set(self.ingredients) == needed
                    and not self.smoker_status[own_ingredient]
            ):
                print(f"Курильщик с {own_ingredient} берёт ингредиенты и начинает курить")
                self.ingredients = []
                self.table_busy = False
                self.smoker_status[own_ingredient] = True
                self.agent_sem.release()
                return True
        return False

    def finish_smoking(self, own_ingredient):
        """
        вызывается после 5 секунд курения
        (то есть сигарета выкурена и курильщик может брать ингридиенты со стола)
        уведомляем всех, что кто-то освободился
        :param own_ingredient: один из ингридиентов(табак, бумага, спички)
        """
        with self.table_mutex:
            print(f"Курильщик с {own_ingredient} закончил курить")
            self.smoker_status[own_ingredient] = False
        self.smoker_sem.release()


def agent(table: Table):
    """
    агент бесконечно кладёт ингредиенты
    :param table: Экземпляр класса Table
    """
    while True:
        first, second = random.sample(INGREDIENTS, 2)
        table.place_ingredients(first, second)
        time.sleep(0.1)  # просто пауза между действиями агента


def smoker(table: Table, own_ingredient: str):
    """
    :param table: экземпляр класса Table
    :param own_ingredient: один из ингридиентов(табак, бумага, спички)
    :return:
    """
    def smoke():
        """
        запускает процесс курения
        :return:
        """
        time.sleep(5)
        table.finish_smoking(own_ingredient)

    # Проверяет, можно ли взять ингридиенты
    while True:
        table.smoker_sem.acquire()  # подождать, когда кто-то положит ингредиенты

        if table.try_take(own_ingredient):
            threading.Thread(target=smoke, daemon=True).start()
        else:
            # если ингредиенты не подошли или он курит — вернуть семафор,
            # чтобы другие курильщики попробовали
            table.smoker_sem.release()

        time.sleep(1)


def main():
    """
    Ининциализируем экземпляр класса
    Запускаем потоки
    :return:
    """
    table = Table()

    threads = [
        threading.Thread(target=agent, args=(table,), daemon=True),
        threading.Thread(target=smoker, args=(table, "табак"), daemon=True),
        threading.Thread(target=smoker, args=(table, "бумага"), daemon=True),
        threading.Thread(target=smoker, args=(table, "спички"), daemon=True),
    ]

    for thread in threads:
        thread.start()

    while True:
        time.sleep(2)

if __name__ == "__main__":
    main()
