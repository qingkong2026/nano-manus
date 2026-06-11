# 获取页面的可视内容 js 代码
GET_VISIBLE_CONTENT_FUNC = """
() => {
  // 1. 定义变量存储所有可视元素+视口的宽高
  const visibleElements = [];
  const viewportHeight = window.innerHeight;
  const viewportWidth = window.innerWidth;

  // 2. 获取页面上的所有元素（包含可见+不可见）
  const elements = document.querySelectorAll("body *");

  // 3. 循环遍历所有 dom 逐个处理
  for (let i = 0; i < elements.length; i++) {
    // 获取 dom 元素的尺寸+位置
    const element = elements[i];
    const rect = element.getBoundingClientRect();

    // 判断元素的宽高，只要有一个为0就表示不可见
    if (rect.height == 0 || rect.width == 0) continue;

    // 排除完全不在当前视口内的元素
    if (
      rect.bottom < 0 ||
      rect.top > viewportHeight ||
      rect.right < 0 ||
      rect.left > viewportWidth
    )
      continue;

    // 7.使用样式来判断当前元素是否隐藏
    const style = window.getComputedStyle(element);
    if (
      style.display === "none" || // 块隐藏
      style.visibility === "hidden" || // 不可见
      style.opacity === "0" // 透明度
    )
      continue;

    // 如果 element 为意义的节点/元素，则添加进来
    if (
      element.innerText ||
      element.tagName === "IMG" ||
      element.tagName === "INPUT" ||
      element.tagName === "BUTTON"
    )
      visibleElements.push(element.outerHTML);
  }
  // 9.将所有的可视元素组装成字符串并拼接到 div 标签中直接返回
  return `<div>${visibleElements.join(" ")}</div>`;
};

"""


# 获取页面可交互元素 js 代码
GET_INTERACTIVE_ELEMENT_FUNC = """
() => {
  // 1.定义变量存储激活元素列表 + 视口宽高
  const interactiveElements = [];
  const viewportHeight = window.innerHeight;
  const viewportWidth = window.innerWidth;

  // 2.获取页面上所有可交互的元素，包括：按钮、a标签、输入框、文本域、下拉菜单、按钮、tab等
  const elements = document.querySelectorAll(
    'button, a, input, textarea, select, [role="button"], [tabindex]:not([tabindex="-1"])',
  );

  // 3.定义变量用于生成连续的唯一索引
  let validElementIndex = 0;

  // 4.循环遍历所有元素
  for (let i = 0; i < elements.length; i++) {
    // 5.取出对应元素并获取尺寸 + 位置
    const element = elements[i];
    const rect = element.getBoundingClientRect();

    // 6.宽高任意为0则跳过这条元素
    if (rect.width === 0 || rect.height === 0) continue;

    // 7.视口不可见元素则跳过
    if (
      rect.bottom < 0 ||
      rect.top > viewportHeight ||
      rect.right < 0 ||
      rect.left > viewportWidth
    )
      continue;

    // 8.样式不可见则跳过该元素
    const style = window.getComputedStyle(element);
    if (
      style.display === "none" ||
      style.visibility === "hidden" ||
      style.opacity === "0"
    )
      continue;

    // 9.获取元素的标签名并转换成小写，同时提取标签内容
    let tagName = element.tagName.toLowerCase();
    let text = "";

    // 10.根据标签类型不同处理不同的逻辑，首先是输入框、文本域、下拉菜单
    if (element.value && ["input", "textarea", "select"].includes(tagName)) {
      text = element.value;

      // 11.标签为输入框则执行以下代码，记录 label 和 placeholder
      if (tagName === "input") {
        // 12.查询输入框的 label 是否存在并赋值
        let labelText = "";
        if (element.id) {
          const label = document.querySelector(`label[for="${element.id}"]`);
          if (label) {
            labelText = label.innerText.trim();
          }
        }

        // 13.查找父级或同级的 label (当没有 for 属性绑定时)
        if (!labelText) {
          const parentLabel = element.closest("label");
          if (parentLabel) {
            labelText = parentLabel.innerText
              .trim()
              .replace(element.value, "")
              .trim();
          }
        }

        // 14.拼接 label 信息
        if (labelText) {
          text = `[Label: ${labelText}] ${text}`;
        }

        // 15.拼接 placeholder 信息
        if (element.placeholder) {
          text = `${text} [Placeholder: ${element.placeholder}]`;
        }
      }
    } else if (element.innerText) {
      // 16.普通元素则提取内部文本并剔除多余空格（如<button>提交</button>）
      text = element.innerText.trim().replace(/\s+/g, " ");
    } else if (element.alt) {
      // 17.图片按钮，取 alt 属性
      text = element.alt;
    } else if (element.title) {
      // 取 title 属性
      text = element.title;
    } else if (element.placeholder) {
      // 提取 placeholder
      text = `[Placeholder: ${element.placeholder}]`;
    } else if (element.type) {
      // 兜底逻辑将元素的类型作为文本描述
      text = `[${element.type}]`;

      // 针对没有值的 Input ，再次尝试获取 Label 和 placeholder
      if (tagName === "input") {
        let labelText = "";
        if (element.id) {
          const label = document.querySelector(`label`);
          if (label) {
            labelText = label.innerText.trim();
          }
        }

        if (labelText) {
          text = `[Label: ${labelText}] ${text}`;
        }

        if (element.placeholder) {
          text = `${text} [Placeholder: ${element.placeholder}]`;
        }
      }
    } else {
      // 都不满足，则设置为 No Text
      text = "[No Text]";
    }

    // 检测文本长度是否超过100，如果是则剔除多余的部分
    if (text.length > 100) {
      text = text.substring(0, 97) + "...";
    }

    // 为当前元素添加 data-manus-id 的属性，值为 manus-element-idx, 这样可以通过索引
    element.setAttribute("data-manus-id", `manus-element-${validElementIndex}`);

    // 构建 css 选择器
    const selector = `[data-manus-id="manus-element-${validElementIndex}"]`;

    // 将索引、标签名、文本、选择器添加到激活元素列表中
    interactiveElements.push({
      index: validElementIndex,
      tag: tagName,
      text: text,
      selector: selector,
    });

    // 索引自增
    validElementIndex++;
  }

  // 最终返回所有激活元素数据
  return interactiveElements;
};

"""

# 在执行代码前先执行这段 js 代码，实现将 console.log 内存存储到 window.console.logs 中
INJECT_CONSOLE_LOGS_FUNC = """
() => {
  // 1.定义变量存储控制台输出日志
  window.console.logs = [];

  // 2.重写 window.console.log 函数
  const originalLog = console.log;
  console.log = (...args) => {
    window.console.logs.push(args.join(" "));
    originalLog.apply(console, args);
  };
};
"""